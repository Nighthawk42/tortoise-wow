#include "PlayerbotDialogueGateway.h"

#include "PlayerbotAIConfig.h"
#include "World.h"

#include <boost/asio/connect.hpp>
#include <boost/asio/ip/tcp.hpp>
#include <boost/beast/core.hpp>
#include <boost/beast/http.hpp>
#include <boost/beast/version.hpp>

#include <algorithm>
#include <utility>

using namespace ai;

namespace
{
    namespace asio = boost::asio;
    namespace beast = boost::beast;
    namespace http = beast::http;
    using tcp = asio::ip::tcp;

    std::atomic<std::uint64_t> nextContextId{1};

    std::string MakeOutcomePath(const std::string& dialoguePath)
    {
        const std::string suffix = "/v1/dialogue";
        if (dialoguePath.size() >= suffix.size() &&
            dialoguePath.compare(dialoguePath.size() - suffix.size(), suffix.size(), suffix) == 0)
        {
            return dialoguePath.substr(0, dialoguePath.size() - suffix.size()) + "/v1/outcomes";
        }
        return "/v1/outcomes";
    }
}

PlayerbotDialogueGateway& PlayerbotDialogueGateway::instance()
{
    static PlayerbotDialogueGateway gateway;
    return gateway;
}

std::uint64_t PlayerbotDialogueGateway::NextContextId()
{
    return nextContextId.fetch_add(1, std::memory_order_relaxed);
}

PlayerbotDialogueGateway::~PlayerbotDialogueGateway()
{
    {
        std::lock_guard<std::mutex> lock(mutex_);
        stopping_ = true;
    }
    workAvailable_.notify_all();
    for (std::thread& worker : workers_)
        if (worker.joinable())
            worker.join();
}

bool PlayerbotDialogueGateway::StartLocked()
{
    if (started_)
        return !stopping_;

    settings_.hostname = sPlayerbotAIConfig.sidecarEndpointUrl.hostname;
    settings_.dialoguePath = sPlayerbotAIConfig.sidecarEndpointUrl.path.empty()
        ? "/v1/dialogue" : sPlayerbotAIConfig.sidecarEndpointUrl.path;
    settings_.outcomePath = MakeOutcomePath(settings_.dialoguePath);
    settings_.serverId = sPlayerbotAIConfig.sidecarServerId;
    settings_.serviceToken = sPlayerbotAIConfig.sidecarServiceToken;
    settings_.realmId = realmID;
    settings_.port = static_cast<std::uint16_t>(sPlayerbotAIConfig.sidecarEndpointUrl.port);
    settings_.requestTimeoutMs = sPlayerbotAIConfig.sidecarRequestTimeoutMs;
    settings_.queueCapacity = sPlayerbotAIConfig.sidecarQueueCapacity;
    settings_.maxPendingPerBot = sPlayerbotAIConfig.sidecarMaxPendingPerBot;
    settings_.workerCount = sPlayerbotAIConfig.sidecarWorkerCount;
    settings_.playerCooldownMs = sPlayerbotAIConfig.sidecarPlayerCooldownMs;
    try
    {
        workers_.reserve(settings_.workerCount);
        for (std::size_t index = 0; index < settings_.workerCount; ++index)
            workers_.emplace_back(&PlayerbotDialogueGateway::WorkerLoop, this);
        started_ = true;
        return true;
    }
    catch (...)
    {
        started_ = true;
        stopping_ = true;
        workAvailable_.notify_all();
        return false;
    }
}

bool PlayerbotDialogueGateway::TrySubmit(PlayerbotDialogueRequest request)
{
    if (!sPlayerbotAIConfig.sidecarEnabled || request.botGuid == 0 || request.speakerGuid == 0)
        return false;

    const auto now = std::chrono::steady_clock::now();
    const std::uint64_t pairKey = (static_cast<std::uint64_t>(request.botGuid) << 32) |
        static_cast<std::uint64_t>(request.speakerGuid);
    {
        std::lock_guard<std::mutex> lock(mutex_);
        if (!StartLocked())
            return false;
        const auto pending = pendingByBot_.find(request.botGuid);
        if (stopping_ || requests_.size() >= settings_.queueCapacity)
        {
            queueRejected_.fetch_add(1, std::memory_order_relaxed);
            return false;
        }
        if (pending != pendingByBot_.end() && pending->second >= settings_.maxPendingPerBot)
        {
            pendingRejected_.fetch_add(1, std::memory_order_relaxed);
            return false;
        }

        const auto accepted = lastAcceptedByPair_.find(pairKey);
        if (accepted != lastAcceptedByPair_.end() &&
            now - accepted->second < std::chrono::milliseconds(settings_.playerCooldownMs))
        {
            cooldownRejected_.fetch_add(1, std::memory_order_relaxed);
            return false;
        }

        request.requestId = PlayerbotDialogueContract::MakeRequestId();
        request.occurredAt = std::chrono::system_clock::now();
        request.deadline = request.occurredAt + std::chrono::milliseconds(settings_.requestTimeoutMs);
        requests_.push_back(std::move(request));
        ++pendingByBot_[requests_.back().botGuid];
        lastAcceptedByPair_[pairKey] = now;
        acceptedOrder_.emplace_back(pairKey, now);
        while (acceptedOrder_.size() > settings_.queueCapacity * 8)
        {
            const auto oldest = acceptedOrder_.front();
            acceptedOrder_.pop_front();
            const auto current = lastAcceptedByPair_.find(oldest.first);
            if (current != lastAcceptedByPair_.end() && current->second == oldest.second)
                lastAcceptedByPair_.erase(current);
        }
        accepted_.fetch_add(1, std::memory_order_relaxed);
    }
    workAvailable_.notify_one();
    return true;
}

bool PlayerbotDialogueGateway::TryTake(std::uint32_t botGuid, PlayerbotDialogueResponse& response)
{
    std::lock_guard<std::mutex> lock(mutex_);
    auto found = completedByBot_.find(botGuid);
    if (found == completedByBot_.end() || found->second.empty())
        return false;

    response = std::move(found->second.front());
    found->second.pop_front();
    --completedCount_;
    if (found->second.empty())
        completedByBot_.erase(found);
    return true;
}

PlayerbotDialogueGatewayMetrics PlayerbotDialogueGateway::Metrics() const
{
    PlayerbotDialogueGatewayMetrics metrics;
    metrics.accepted = accepted_.load(std::memory_order_relaxed);
    metrics.queueRejected = queueRejected_.load(std::memory_order_relaxed);
    metrics.pendingRejected = pendingRejected_.load(std::memory_order_relaxed);
    metrics.cooldownRejected = cooldownRejected_.load(std::memory_order_relaxed);
    metrics.completed = completed_.load(std::memory_order_relaxed);
    metrics.failed = failed_.load(std::memory_order_relaxed);
    metrics.late = late_.load(std::memory_order_relaxed);
    metrics.responseQueueDropped = responseQueueDropped_.load(std::memory_order_relaxed);
    metrics.outcomeQueueDropped = outcomeQueueDropped_.load(std::memory_order_relaxed);
    return metrics;
}

void PlayerbotDialogueGateway::ReportOutcome(
    const std::string& requestId,
    const std::string& outcome,
    const std::string& reason)
{
    if (requestId.empty())
        return;
    {
        std::lock_guard<std::mutex> lock(mutex_);
        if (!started_ || stopping_ || outcomes_.size() >= settings_.queueCapacity)
        {
            outcomeQueueDropped_.fetch_add(1, std::memory_order_relaxed);
            return;
        }
        outcomes_.push_back({requestId, outcome, reason});
    }
    workAvailable_.notify_one();
}

void PlayerbotDialogueGateway::FinishDialogue(const PlayerbotDialogueRequest& request)
{
    std::lock_guard<std::mutex> lock(mutex_);
    auto found = pendingByBot_.find(request.botGuid);
    if (found == pendingByBot_.end())
        return;
    if (--found->second == 0)
        pendingByBot_.erase(found);
}

bool PlayerbotDialogueGateway::QueueCompleted(PlayerbotDialogueResponse response)
{
    std::lock_guard<std::mutex> lock(mutex_);
    const auto now = std::chrono::system_clock::now();
    for (auto byBot = completedByBot_.begin(); byBot != completedByBot_.end();)
    {
        auto& queued = byBot->second;
        while (!queued.empty() && now > queued.front().deadline)
        {
            if (outcomes_.size() < settings_.queueCapacity)
                outcomes_.push_back({queued.front().requestId, "expired", "response_expired_in_core_queue"});
            else
                outcomeQueueDropped_.fetch_add(1, std::memory_order_relaxed);
            queued.pop_front();
            --completedCount_;
            late_.fetch_add(1, std::memory_order_relaxed);
        }
        if (queued.empty())
            byBot = completedByBot_.erase(byBot);
        else
            ++byBot;
    }
    if (stopping_ || completedCount_ >= settings_.queueCapacity)
        return false;
    completedByBot_[response.botGuid].push_back(std::move(response));
    ++completedCount_;
    return true;
}

void PlayerbotDialogueGateway::WorkerLoop()
{
    for (;;)
    {
        PlayerbotDialogueRequest request;
        OutcomeJob outcome;
        bool hasRequest = false;
        {
            std::unique_lock<std::mutex> lock(mutex_);
            workAvailable_.wait(lock, [this]() {
                return stopping_ || !requests_.empty() || !outcomes_.empty();
            });
            if (stopping_)
                return;
            if (!requests_.empty())
            {
                request = std::move(requests_.front());
                requests_.pop_front();
                hasRequest = true;
            }
            else
            {
                outcome = std::move(outcomes_.front());
                outcomes_.pop_front();
            }
        }

        std::string responseBody;
        std::string error;
        if (hasRequest)
        {
            const std::string body = PlayerbotDialogueContract::Serialize(
                request, settings_.serverId, settings_.realmId);
            const bool posted = PostJson(settings_.dialoguePath, body, 200, responseBody, error);
            PlayerbotDialogueResponse response;
            const bool parsed = posted && PlayerbotDialogueContract::ParseCompletedResponse(
                responseBody, request, response, error);
            FinishDialogue(request);

            if (!parsed)
            {
                failed_.fetch_add(1, std::memory_order_relaxed);
                continue;
            }
            if (std::chrono::system_clock::now() > request.deadline)
            {
                late_.fetch_add(1, std::memory_order_relaxed);
                ReportOutcome(request.requestId, "expired", "response_arrived_after_deadline");
                continue;
            }
            if (!QueueCompleted(std::move(response)))
            {
                responseQueueDropped_.fetch_add(1, std::memory_order_relaxed);
                ReportOutcome(request.requestId, "bot_unavailable", "core_response_queue_full");
            }
            else
                completed_.fetch_add(1, std::memory_order_relaxed);
        }
        else
        {
            const std::string body = PlayerbotDialogueContract::SerializeOutcome(
                outcome.requestId, settings_.serverId, outcome.outcome, outcome.reason);
            PostJson(settings_.outcomePath, body, 202, responseBody, error);
        }
    }
}

bool PlayerbotDialogueGateway::PostJson(
    const std::string& path,
    const std::string& body,
    unsigned expectedStatus,
    std::string& responseBody,
    std::string& error) const
{
    try
    {
        asio::io_context io;
        tcp::resolver resolver(io);
        beast::tcp_stream stream(io);
        stream.expires_after(std::chrono::milliseconds(settings_.requestTimeoutMs));
        const auto endpoints = resolver.resolve(settings_.hostname, std::to_string(settings_.port));
        stream.connect(endpoints);

        http::request<http::string_body> request{http::verb::post, path, 11};
        request.set(http::field::host, settings_.hostname);
        request.set(http::field::user_agent, "tortoise-playerbots/1.0");
        request.set(http::field::content_type, "application/json");
        if (!settings_.serviceToken.empty())
            request.set(http::field::authorization, "Bearer " + settings_.serviceToken);
        request.body() = body;
        request.prepare_payload();
        http::write(stream, request);

        beast::flat_buffer buffer;
        http::response_parser<http::string_body> parser;
        parser.body_limit(64 * 1024);
        http::read(stream, buffer, parser);
        const http::response<http::string_body> response = parser.release();
        responseBody = response.body();

        beast::error_code shutdownError;
        stream.socket().shutdown(tcp::socket::shutdown_both, shutdownError);
        if (response.result_int() != expectedStatus)
        {
            error = "http_status_" + std::to_string(response.result_int());
            return false;
        }
        return true;
    }
    catch (const std::exception& exception)
    {
        error = exception.what();
        return false;
    }
}

#pragma once

#include "PlayerbotDialogueContract.h"

#include <atomic>
#include <chrono>
#include <condition_variable>
#include <cstdint>
#include <deque>
#include <mutex>
#include <string>
#include <thread>
#include <unordered_map>
#include <vector>

namespace ai
{
    struct PlayerbotDialogueGatewayMetrics
    {
        std::uint64_t accepted = 0;
        std::uint64_t queueRejected = 0;
        std::uint64_t pendingRejected = 0;
        std::uint64_t cooldownRejected = 0;
        std::uint64_t completed = 0;
        std::uint64_t failed = 0;
        std::uint64_t late = 0;
        std::uint64_t responseQueueDropped = 0;
        std::uint64_t outcomeQueueDropped = 0;
    };

    class PlayerbotDialogueGateway
    {
    public:
        static PlayerbotDialogueGateway& instance();
        static std::uint64_t NextContextId();

        bool TrySubmit(PlayerbotDialogueRequest request);
        bool TryTake(std::uint32_t botGuid, PlayerbotDialogueResponse& response);
        PlayerbotDialogueGatewayMetrics Metrics() const;
        void ReportOutcome(
            const std::string& requestId,
            const std::string& outcome,
            const std::string& reason = std::string());

        ~PlayerbotDialogueGateway();

    private:
        struct Settings
        {
            std::string hostname;
            std::string dialoguePath;
            std::string outcomePath;
            std::string serverId;
            std::string serviceToken;
            std::uint32_t realmId = 1;
            std::uint16_t port = 8100;
            std::uint32_t requestTimeoutMs = 8000;
            std::size_t queueCapacity = 64;
            std::size_t maxPendingPerBot = 1;
            std::size_t workerCount = 2;
            std::uint32_t playerCooldownMs = 5000;
        };

        struct OutcomeJob
        {
            std::string requestId;
            std::string outcome;
            std::string reason;
        };

        PlayerbotDialogueGateway() = default;
        PlayerbotDialogueGateway(const PlayerbotDialogueGateway&) = delete;
        PlayerbotDialogueGateway& operator=(const PlayerbotDialogueGateway&) = delete;

        bool StartLocked();
        void WorkerLoop();
        bool PostJson(const std::string& path, const std::string& body, unsigned expectedStatus,
            std::string& responseBody, std::string& error) const;
        void FinishDialogue(const PlayerbotDialogueRequest& request);
        bool QueueCompleted(PlayerbotDialogueResponse response);

        Settings settings_;
        bool started_ = false;
        bool stopping_ = false;
        std::mutex mutex_;
        std::condition_variable workAvailable_;
        std::deque<PlayerbotDialogueRequest> requests_;
        std::deque<OutcomeJob> outcomes_;
        std::unordered_map<std::uint32_t, std::size_t> pendingByBot_;
        std::unordered_map<std::uint64_t, std::chrono::steady_clock::time_point> lastAcceptedByPair_;
        std::deque<std::pair<std::uint64_t, std::chrono::steady_clock::time_point>> acceptedOrder_;
        std::unordered_map<std::uint32_t, std::deque<PlayerbotDialogueResponse>> completedByBot_;
        std::size_t completedCount_ = 0;
        std::vector<std::thread> workers_;
        std::atomic<std::uint64_t> accepted_{0};
        std::atomic<std::uint64_t> queueRejected_{0};
        std::atomic<std::uint64_t> pendingRejected_{0};
        std::atomic<std::uint64_t> cooldownRejected_{0};
        std::atomic<std::uint64_t> completed_{0};
        std::atomic<std::uint64_t> failed_{0};
        std::atomic<std::uint64_t> late_{0};
        std::atomic<std::uint64_t> responseQueueDropped_{0};
        std::atomic<std::uint64_t> outcomeQueueDropped_{0};
    };
}

#define sPlayerbotDialogueGateway ai::PlayerbotDialogueGateway::instance()

#include "PlayerbotDialogueContract.h"

#include "rapidjson/document.h"
#include "rapidjson/stringbuffer.h"
#include "rapidjson/writer.h"

#include <array>
#include <ctime>
#include <cstdio>
#include <random>

using namespace ai;

namespace
{
    void WriteString(rapidjson::Writer<rapidjson::StringBuffer>& writer, const std::string& value)
    {
        writer.String(value.data(), static_cast<rapidjson::SizeType>(value.size()));
    }

    void WriteStringArray(
        rapidjson::Writer<rapidjson::StringBuffer>& writer,
        const std::vector<std::string>& values)
    {
        writer.StartArray();
        for (const std::string& value : values)
            WriteString(writer, value);
        writer.EndArray();
    }
}

std::string PlayerbotDialogueContract::MakeRequestId()
{
    std::array<unsigned char, 16> bytes;
    static thread_local std::mt19937_64 generator(std::random_device{}());
    for (size_t index = 0; index < bytes.size(); index += sizeof(std::uint64_t))
    {
        std::uint64_t value = generator();
        for (size_t offset = 0; offset < sizeof(std::uint64_t); ++offset)
            bytes[index + offset] = static_cast<unsigned char>(value >> (offset * 8));
    }
    bytes[6] = static_cast<unsigned char>((bytes[6] & 0x0f) | 0x40);
    bytes[8] = static_cast<unsigned char>((bytes[8] & 0x3f) | 0x80);

    char result[37];
    std::snprintf(
        result,
        sizeof(result),
        "%02x%02x%02x%02x-%02x%02x-%02x%02x-%02x%02x-%02x%02x%02x%02x%02x%02x",
        bytes[0], bytes[1], bytes[2], bytes[3], bytes[4], bytes[5], bytes[6], bytes[7],
        bytes[8], bytes[9], bytes[10], bytes[11], bytes[12], bytes[13], bytes[14], bytes[15]);
    return result;
}

std::string PlayerbotDialogueContract::FormatUtc(std::chrono::system_clock::time_point value)
{
    const std::time_t raw = std::chrono::system_clock::to_time_t(value);
    std::tm utc{};
#ifdef _WIN32
    gmtime_s(&utc, &raw);
#else
    gmtime_r(&raw, &utc);
#endif
    char buffer[32];
    std::strftime(buffer, sizeof(buffer), "%Y-%m-%dT%H:%M:%SZ", &utc);
    return buffer;
}

std::string PlayerbotDialogueContract::Serialize(
    const PlayerbotDialogueRequest& request,
    const std::string& serverId,
    std::uint32_t realmId)
{
    rapidjson::StringBuffer buffer;
    rapidjson::Writer<rapidjson::StringBuffer> writer(buffer);
    writer.StartObject();
    writer.Key("contract_version"); writer.String("1.0");
    writer.Key("request_id"); WriteString(writer, request.requestId);
    writer.Key("server_id"); WriteString(writer, serverId);
    writer.Key("realm_id"); writer.Uint(realmId);
    writer.Key("deadline"); WriteString(writer, FormatUtc(request.deadline));

    writer.Key("event"); writer.StartObject();
    writer.Key("type"); writer.String("dialogue.requested");
    writer.Key("occurred_at"); WriteString(writer, FormatUtc(request.occurredAt));
    writer.Key("channel"); WriteString(writer, request.channel);
    writer.Key("text"); WriteString(writer, request.text);
    writer.Key("language"); WriteString(writer, request.language);
    writer.EndObject();

    writer.Key("bot"); writer.StartObject();
    writer.Key("actor_id");
    WriteString(writer, "realm:" + std::to_string(realmId) + ":character:" + std::to_string(request.botGuid));
    writer.Key("character_guid_low"); writer.Uint(request.botGuid);
    writer.Key("name"); WriteString(writer, request.botName);
    writer.Key("level"); writer.Uint(request.botLevel);
    writer.Key("race"); WriteString(writer, request.botRace);
    writer.Key("class"); WriteString(writer, request.botClass);
    writer.Key("zone"); WriteString(writer, request.zone);
    writer.Key("subzone"); WriteString(writer, request.subzone);
    writer.Key("group_role"); writer.Null();
    writer.EndObject();

    writer.Key("speaker"); writer.StartObject();
    writer.Key("actor_id");
    WriteString(writer, "realm:" + std::to_string(realmId) + ":character:" + std::to_string(request.speakerGuid));
    writer.Key("display_name"); WriteString(writer, request.speakerName);
    writer.Key("kind"); WriteString(writer, request.speakerKind);
    writer.Key("relationship"); WriteString(writer, request.relationship);
    writer.EndObject();

    writer.Key("limits"); writer.StartObject();
    writer.Key("max_utf8_bytes"); writer.Uint(request.maxUtf8Bytes);
    writer.Key("allowed_output"); writer.StartArray(); writer.String("chat.text"); writer.EndArray();
    writer.EndObject();

    writer.Key("context"); writer.StartObject();
    writer.Key("recent_dialogue"); WriteStringArray(writer, request.recentDialogue);
    writer.Key("facts"); WriteStringArray(writer, request.facts);
    writer.EndObject();
    writer.EndObject();
    return std::string(buffer.GetString(), buffer.GetSize());
}

std::string PlayerbotDialogueContract::SerializeOutcome(
    const std::string& requestId,
    const std::string& serverId,
    const std::string& outcome,
    const std::string& reason)
{
    rapidjson::StringBuffer buffer;
    rapidjson::Writer<rapidjson::StringBuffer> writer(buffer);
    writer.StartObject();
    writer.Key("contract_version"); writer.String("1.0");
    writer.Key("request_id"); WriteString(writer, requestId);
    writer.Key("server_id"); WriteString(writer, serverId);
    writer.Key("occurred_at"); WriteString(writer, FormatUtc(std::chrono::system_clock::now()));
    writer.Key("outcome"); WriteString(writer, outcome);
    if (!reason.empty())
    {
        writer.Key("reason"); WriteString(writer, reason);
    }
    writer.EndObject();
    return std::string(buffer.GetString(), buffer.GetSize());
}

bool PlayerbotDialogueContract::ParseCompletedResponse(
    const std::string& body,
    const PlayerbotDialogueRequest& request,
    PlayerbotDialogueResponse& response,
    std::string& error)
{
    rapidjson::Document document;
    document.Parse<rapidjson::kParseValidateEncodingFlag>(body.data(), body.size());
    if (document.HasParseError() || !document.IsObject())
    {
        error = "malformed_json";
        return false;
    }
    if (!document.HasMember("request_id") || !document["request_id"].IsString() ||
        request.requestId != document["request_id"].GetString())
    {
        error = "request_id_mismatch";
        return false;
    }
    if (!document.HasMember("status") || !document["status"].IsString() ||
        std::string(document["status"].GetString()) != "completed")
    {
        error = document.HasMember("error") ? "sidecar_failure" : "invalid_status";
        return false;
    }
    if (!document.HasMember("candidate") || !document["candidate"].IsObject())
    {
        error = "missing_candidate";
        return false;
    }
    const rapidjson::Value& candidate = document["candidate"];
    if (!candidate.HasMember("type") || !candidate["type"].IsString() ||
        std::string(candidate["type"].GetString()) != "chat.text" ||
        !candidate.HasMember("text") || !candidate["text"].IsString() ||
        !candidate.HasMember("language") || !candidate["language"].IsString())
    {
        error = "invalid_candidate";
        return false;
    }
    const size_t textSize = candidate["text"].GetStringLength();
    if (textSize == 0 || textSize > request.maxUtf8Bytes)
    {
        error = "invalid_text_size";
        return false;
    }
    response.requestId = request.requestId;
    response.botGuid = request.botGuid;
    response.contextId = request.contextId;
    response.speakerGuid = request.speakerGuid;
    response.speakerName = request.speakerName;
    response.text.assign(candidate["text"].GetString(), textSize);
    response.language = candidate["language"].GetString();
    response.deadline = request.deadline;
    return true;
}

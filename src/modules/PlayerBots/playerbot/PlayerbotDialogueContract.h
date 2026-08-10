#pragma once

#include <chrono>
#include <cstdint>
#include <string>
#include <vector>

namespace ai
{
    struct PlayerbotDialogueRequest
    {
        std::string requestId;
        std::uint32_t botGuid = 0;
        std::uint64_t contextId = 0;
        std::uint32_t speakerGuid = 0;
        std::string botName;
        std::uint32_t botLevel = 1;
        std::string botRace;
        std::string botClass;
        std::string zone;
        std::string subzone;
        std::string speakerName;
        std::string speakerKind = "player";
        std::string relationship = "stranger";
        std::string channel = "whisper";
        std::string language = "common";
        std::string text;
        std::vector<std::string> recentDialogue;
        std::vector<std::string> facts;
        std::uint32_t maxUtf8Bytes = 255;
        std::chrono::system_clock::time_point occurredAt;
        std::chrono::system_clock::time_point deadline;
    };

    struct PlayerbotDialogueResponse
    {
        std::string requestId;
        std::uint32_t botGuid = 0;
        std::uint64_t contextId = 0;
        std::uint32_t speakerGuid = 0;
        std::string speakerName;
        std::string text;
        std::string language;
        std::chrono::system_clock::time_point deadline;
    };

    class PlayerbotDialogueContract
    {
    public:
        static std::string MakeRequestId();
        static std::string FormatUtc(std::chrono::system_clock::time_point value);
        static std::string Serialize(
            const PlayerbotDialogueRequest& request,
            const std::string& serverId,
            std::uint32_t realmId);
        static std::string SerializeOutcome(
            const std::string& requestId,
            const std::string& serverId,
            const std::string& outcome,
            const std::string& reason);
        static bool ParseCompletedResponse(
            const std::string& body,
            const PlayerbotDialogueRequest& request,
            PlayerbotDialogueResponse& response,
            std::string& error);
    };
}

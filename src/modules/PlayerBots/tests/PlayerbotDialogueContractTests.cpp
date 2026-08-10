#include "PlayerbotDialogueContract.h"

#include "rapidjson/document.h"

#include <chrono>
#include <iostream>
#include <string>

using namespace ai;

namespace
{
    bool Check(bool condition, const char* expression, int line)
    {
        if (condition)
            return true;
        std::cerr << "Check failed at line " << line << ": " << expression << '\n';
        return false;
    }

#define CHECK(expression) do { if (!Check((expression), #expression, __LINE__)) return 1; } while (false)

    PlayerbotDialogueRequest MakeRequest()
    {
        PlayerbotDialogueRequest request;
        request.requestId = PlayerbotDialogueContract::MakeRequestId();
        request.botGuid = 4821;
        request.contextId = 17;
        request.speakerGuid = 9001;
        request.botName = "Arielle";
        request.botLevel = 32;
        request.botRace = "Human";
        request.botClass = "Mage";
        request.zone = "Stranglethorn Vale";
        request.subzone = "Booty Bay";
        request.speakerName = "Tester";
        request.text = "Want to run a dungeon?";
        request.occurredAt = std::chrono::system_clock::now();
        request.deadline = request.occurredAt + std::chrono::seconds(8);
        return request;
    }
}

int main()
{
    const std::string id = PlayerbotDialogueContract::MakeRequestId();
    CHECK(id.size() == 36);
    CHECK(id[8] == '-' && id[13] == '-' && id[18] == '-' && id[23] == '-');
    CHECK(id[14] == '4');
    CHECK(id[19] == '8' || id[19] == '9' || id[19] == 'a' || id[19] == 'b');

    PlayerbotDialogueRequest request = MakeRequest();
    const std::string serialized = PlayerbotDialogueContract::Serialize(request, "turtle-dev", 1);
    rapidjson::Document document;
    document.Parse(serialized.data(), serialized.size());
    CHECK(!document.HasParseError());
    CHECK(document["realm_id"].GetUint() == 1);
    CHECK(document["bot"]["character_guid_low"].GetUint() == request.botGuid);
    CHECK(!document["bot"].HasMember("persona_id"));
    CHECK(std::string(document["event"]["text"].GetString()) == request.text);

    const std::string completed =
        "{\"contract_version\":\"1.0\",\"request_id\":\"" + request.requestId +
        "\",\"status\":\"completed\",\"candidate\":{\"type\":\"chat.text\","
        "\"text\":\"Sure, give me a minute.\",\"language\":\"common\"},"
        "\"persona\":{\"id\":\"generic-human-mage\",\"revision\":\"1\"}}";
    PlayerbotDialogueResponse response;
    std::string error;
    CHECK(PlayerbotDialogueContract::ParseCompletedResponse(completed, request, response, error));
    CHECK(response.contextId == request.contextId);
    CHECK(response.text == "Sure, give me a minute.");

    std::string wrongId = completed;
    wrongId.replace(wrongId.find(request.requestId), request.requestId.size(),
        "00000000-0000-4000-8000-000000000000");
    CHECK(!PlayerbotDialogueContract::ParseCompletedResponse(wrongId, request, response, error));
    CHECK(error == "request_id_mismatch");
    CHECK(!PlayerbotDialogueContract::ParseCompletedResponse("not-json", request, response, error));
    CHECK(error == "malformed_json");
    std::string invalidUtf8 = completed;
    invalidUtf8.replace(invalidUtf8.find("Sure, give me a minute."), 23, std::string("\xc3\x28", 2));
    CHECK(!PlayerbotDialogueContract::ParseCompletedResponse(invalidUtf8, request, response, error));
    CHECK(error == "malformed_json");

    PlayerbotDialogueRequest shortRequest = request;
    shortRequest.maxUtf8Bytes = 4;
    CHECK(!PlayerbotDialogueContract::ParseCompletedResponse(completed, shortRequest, response, error));
    CHECK(error == "invalid_text_size");

    const std::string outcome = PlayerbotDialogueContract::SerializeOutcome(
        request.requestId, "turtle-dev", "emitted", "");
    document.Parse(outcome.data(), outcome.size());
    CHECK(!document.HasParseError());
    CHECK(std::string(document["outcome"].GetString()) == "emitted");
    CHECK(!document.HasMember("reason"));

    std::cout << "Playerbot dialogue contract tests passed\n";
    return 0;
}

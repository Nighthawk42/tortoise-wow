#
# Copyright (C) 2005-2018 MaNGOS project <http://getmangos.com/>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#

set(LIBRARY_NAME playerbots)

#Add PCH Files
set(bots_PCH "${CMAKE_CURRENT_SOURCE_DIR}/botpch.h")

#Base files
file(GLOB Playerbot_Source ${CMAKE_CURRENT_SOURCE_DIR}/playerbot/*.cpp ${CMAKE_CURRENT_SOURCE_DIR}/playerbot/*.h)
    source_group("Player Bot" FILES ${Playerbot_Source})

file(GLOB AHbot_Source ${CMAKE_CURRENT_SOURCE_DIR}/ahbot/*.cpp ${CMAKE_CURRENT_SOURCE_DIR}/ahbot/*.h)
    source_group("AH Bot" FILES ${AHbot_Source})

#Define base source library
set(LIBRARY_SRCS
    ${Playerbot_Source}
    ${AHbot_Source}
    ${bots_PCH}
    ${CMAKE_CURRENT_SOURCE_DIR}/botpch.cpp
)

#Strategy files
file(GLOB Playerbot_Strategy ${CMAKE_CURRENT_SOURCE_DIR}/playerbot/strategy/*.cpp ${CMAKE_CURRENT_SOURCE_DIR}/playerbot/strategy/*.h)
    source_group("Player Bot\\Strategies" FILES ${Playerbot_Strategy})
    LIST(APPEND LIBRARY_SRCS ${Playerbot_Strategy})

#Action files
file(GLOB Playerbot_Actions ${CMAKE_CURRENT_SOURCE_DIR}/playerbot/strategy/actions/*.cpp ${CMAKE_CURRENT_SOURCE_DIR}/playerbot/strategy/actions/*.h)
    source_group("Player Bot\\Strategies\\Actions" FILES ${Playerbot_Actions})
    LIST(APPEND LIBRARY_SRCS ${Playerbot_Actions})

#Generic files
file(GLOB Playerbot_Generic ${CMAKE_CURRENT_SOURCE_DIR}/playerbot/strategy/generic/*.cpp ${CMAKE_CURRENT_SOURCE_DIR}/playerbot/strategy/generic/*.h)
    source_group("Player Bot\\Strategies\\Generic" FILES ${Playerbot_Generic})
    LIST(APPEND LIBRARY_SRCS ${Playerbot_Generic})

#Trigger files
file(GLOB Playerbot_Triggers ${CMAKE_CURRENT_SOURCE_DIR}/playerbot/strategy/triggers/*.cpp ${CMAKE_CURRENT_SOURCE_DIR}/playerbot/strategy/triggers/*.h)
    source_group("Player Bot\\Strategies\\Triggers" FILES ${Playerbot_Triggers})
    LIST(APPEND LIBRARY_SRCS ${Playerbot_Triggers})

#Value files
file(GLOB Playerbot_Values ${CMAKE_CURRENT_SOURCE_DIR}/playerbot/strategy/values/*.cpp ${CMAKE_CURRENT_SOURCE_DIR}/playerbot/strategy/values/*.h)
    source_group("Player Bot\\Strategies\\Values" FILES ${Playerbot_Values})
    LIST(APPEND LIBRARY_SRCS ${Playerbot_Values})

## Class files

#Druid AI
file(GLOB Playerbot_Druid ${CMAKE_CURRENT_SOURCE_DIR}/playerbot/strategy/druid/*.cpp ${CMAKE_CURRENT_SOURCE_DIR}/playerbot/strategy/druid/*.h)
    source_group("Player Bot\\Strategies\\Druid" FILES ${Playerbot_Druid})
    LIST(APPEND LIBRARY_SRCS ${Playerbot_Druid})

#Hunter AI
file(GLOB Playerbot_Hunter ${CMAKE_CURRENT_SOURCE_DIR}/playerbot/strategy/hunter/*.cpp ${CMAKE_CURRENT_SOURCE_DIR}/playerbot/strategy/hunter/*.h)
    source_group("Player Bot\\Strategies\\Hunter" FILES ${Playerbot_Hunter})
    LIST(APPEND LIBRARY_SRCS ${Playerbot_Hunter})

#Mage AI
file(GLOB Playerbot_Mage ${CMAKE_CURRENT_SOURCE_DIR}/playerbot/strategy/mage/*.cpp ${CMAKE_CURRENT_SOURCE_DIR}/playerbot/strategy/mage/*.h)
    source_group("Player Bot\\Strategies\\Mage" FILES ${Playerbot_Mage})
    LIST(APPEND LIBRARY_SRCS ${Playerbot_Mage})

#Paladin AI
file(GLOB Playerbot_Paladin ${CMAKE_CURRENT_SOURCE_DIR}/playerbot/strategy/paladin/*.cpp ${CMAKE_CURRENT_SOURCE_DIR}/playerbot/strategy/paladin/*.h)
    source_group("Player Bot\\Strategies\\Paladin" FILES ${Playerbot_Paladin})
    LIST(APPEND LIBRARY_SRCS ${Playerbot_Paladin})

#Priest AI
file(GLOB Playerbot_Priest ${CMAKE_CURRENT_SOURCE_DIR}/playerbot/strategy/priest/*.cpp ${CMAKE_CURRENT_SOURCE_DIR}/playerbot/strategy/priest/*.h)
    source_group("Player Bot\\Strategies\\Priest" FILES ${Playerbot_Priest})
    LIST(APPEND LIBRARY_SRCS ${Playerbot_Priest})

#Rogue AI
file(GLOB Playerbot_Rogue ${CMAKE_CURRENT_SOURCE_DIR}/playerbot/strategy/rogue/*.cpp ${CMAKE_CURRENT_SOURCE_DIR}/playerbot/strategy/rogue/*.h)
    source_group("Player Bot\\Strategies\\Rogue" FILES ${Playerbot_Rogue})
    LIST(APPEND LIBRARY_SRCS ${Playerbot_Rogue})

#Shaman AI
file(GLOB Playerbot_Shaman ${CMAKE_CURRENT_SOURCE_DIR}/playerbot/strategy/shaman/*.cpp ${CMAKE_CURRENT_SOURCE_DIR}/playerbot/strategy/shaman/*.h)
    source_group("Player Bot\\Strategies\\Shaman" FILES ${Playerbot_Shaman})
    LIST(APPEND LIBRARY_SRCS ${Playerbot_Shaman})

#Warlock AI
file(GLOB Playerbot_Warlock ${CMAKE_CURRENT_SOURCE_DIR}/playerbot/strategy/warlock/*.cpp ${CMAKE_CURRENT_SOURCE_DIR}/playerbot/strategy/warlock/*.h)
    source_group("Player Bot\\Strategies\\Warlock" FILES ${Playerbot_Warlock})
    LIST(APPEND LIBRARY_SRCS ${Playerbot_Warlock})

#Warrior AI
file(GLOB Playerbot_Warrior ${CMAKE_CURRENT_SOURCE_DIR}/playerbot/strategy/warrior/*.cpp ${CMAKE_CURRENT_SOURCE_DIR}/playerbot/strategy/warrior/*.h)
    source_group("Player Bot\\Strategies\\Warrior" FILES ${Playerbot_Warrior})
    LIST(APPEND LIBRARY_SRCS ${Playerbot_Warrior})

#Deathknight AI
file(GLOB Playerbot_DeathKnight ${CMAKE_CURRENT_SOURCE_DIR}/playerbot/strategy/deathknight/*.cpp ${CMAKE_CURRENT_SOURCE_DIR}/playerbot/strategy/deathknight/*.h)
    source_group("Player Bot\\Strategies\\DeathKnight" FILES ${Playerbot_DeathKnight})
    LIST(APPEND LIBRARY_SRCS ${Playerbot_DeathKnight})

#Test framework
file(GLOB Playerbot_Tests ${CMAKE_CURRENT_SOURCE_DIR}/playerbot/strategy/tests/*.cpp ${CMAKE_CURRENT_SOURCE_DIR}/playerbot/strategy/tests/*.h)
    source_group("Player Bot\\Strategies\\Tests" FILES ${Playerbot_Tests})
    LIST(APPEND LIBRARY_SRCS ${Playerbot_Tests})

# Define ENABLE_PLAYERBOTS if need
if (BUILD_PLAYERBOTS)
  add_definitions(-DENABLE_PLAYERBOTS)
endif()

# Define Core
# Penqle's project name is "TurtleWoW", not "CMaNGOS" or "MaNGOS".
# Define CMANGOS so bot's #ifdef CMANGOS branches activate. We adapt cmangos-style int/uint32 triggered
# flags via shim TRIGGERED_* defines (mapped to bool literals). Without this, both branches skip and
# bot misses critical code paths.
add_definitions(-DCMANGOS)
add_definitions(-DMANGOSBOT_ZERO)

# Define Expansion
if ( ${CMAKE_PROJECT_NAME} MATCHES "Classic")
  add_definitions(-DMANGOSBOT_ZERO)
endif()
if ( ${CMAKE_PROJECT_NAME} MATCHES "TBC")
  add_definitions(-DMANGOSBOT_ONE)
endif()
if ( ${CMAKE_PROJECT_NAME} MATCHES "WoTLK")
  add_definitions(-DMANGOSBOT_TWO)
endif()

# Define ENABLE_MODULES if need
if (BUILD_MODULES)
  add_definitions(-DENABLE_MODULES)
endif()

# Define BUILD_AHBOT if need
if (BUILD_AHBOT)
  add_definitions(-DBUILD_AHBOT)
endif()

if(PCH)
  include_directories(${CMAKE_CURRENT_BINARY_DIR})
endif()

add_library(${LIBRARY_NAME} STATIC ${LIBRARY_SRCS})

if(MSVC)
    # Constrain the MSVC inliner on the bot module only.
    #
    # The vendored cmangos/playerbots tree has very heavily-templated code
    # (Strategy/Action queues, Singleton<> instantiations, the storage
    # proxies in cmangos-compat-shim.h). MSVC's default /Ob2 (auto-inline
    # any function the heuristic deems worthwhile) can ICE the optimizer
    # with C1001 in xhash / vector / type_traits when expanding these
    # template instantiations during phase-2 codegen.
    #
    # /Ob1 honors only explicit `inline` / `__forceinline` keywords — still
    # gets /O2 speed, just doesn't auto-inline normal functions. Drops
    # bot-AI tick performance by an estimated 3-5%; in exchange the bot
    # module builds deterministically. game.lib / scripts.lib / etc. keep
    # the default /Ob2.
    target_compile_options(${LIBRARY_NAME} PRIVATE $<$<CONFIG:Release>:/Ob1>)
endif()

target_link_libraries(${LIBRARY_NAME}
  PRIVATE shared
  PRIVATE Detour
  PRIVATE g3dlite
)
set(PLAYERBOTS_BOOST_COMPONENTS thread filesystem system)
if(POLICY CMP0167)
  cmake_policy(PUSH)
  cmake_policy(SET CMP0167 OLD)
endif()
find_package(Boost 1.70 QUIET COMPONENTS ${PLAYERBOTS_BOOST_COMPONENTS})
if(POLICY CMP0167)
  cmake_policy(POP)
endif()

if(NOT Boost_FOUND)
  if(NOT PLAYERBOTS_FETCH_BOOST)
    message(FATAL_ERROR
      "Playerbots require Boost 1.70+ components thread, filesystem, and system. "
      "Install Boost or configure with -DPLAYERBOTS_FETCH_BOOST=ON.")
  endif()

  message(STATUS "System Boost not found; fetching pinned Boost 1.91.0 for playerbots")
  include(FetchContent)

  # The official Boost release archive contains every header dependency used by
  # playerbots. Limit compiled/configured libraries to the direct requirements
  # and their dependency closure. The archive checksum is published on
  # https://www.boost.org/releases/1.91.0/.
  set(BOOST_INCLUDE_LIBRARIES
    algorithm
    asio
    bimap
    bind
    filesystem
    functional
    smart_ptr
    stacktrace
    system
    thread
    CACHE STRING "Boost libraries required by playerbots" FORCE)
  set(BOOST_ENABLE_CMAKE ON CACHE BOOL "Use Boost's CMake build" FORCE)
  set(BOOST_SKIP_INSTALL_RULES ON CACHE BOOL "Do not install fetched Boost targets" FORCE)
  set(BUILD_TESTING OFF CACHE BOOL "Disable third-party tests" FORCE)

  FetchContent_Declare(
    playerbots_boost
    URL https://archives.boost.io/release/1.91.0/source/boost_1_91_0.tar.gz
    URL_HASH SHA256=5734305f40a76c30f951c9abd409a45a2a19fb546efe4162119250bbe4d3a463
    DOWNLOAD_EXTRACT_TIMESTAMP TRUE)
  FetchContent_MakeAvailable(playerbots_boost)
  message(STATUS "Playerbot fetched Boost source: ${playerbots_boost_SOURCE_DIR}")

  # Release archives intentionally omit the Boost super-project's root
  # CMakeLists.txt even though all modular CMake files are present. Generate the
  # official entry-point shape, then add it after FetchContent has populated the
  # verified archive.
  if(NOT TARGET Boost::thread)
    set(PLAYERBOTS_BOOST_VERSION 1.91.0)
    configure_file(
      ${CMAKE_SOURCE_DIR}/cmake/PlayerbotsBoostRoot.CMakeLists.txt.in
      ${playerbots_boost_SOURCE_DIR}/CMakeLists.txt
      @ONLY)
    # Official release archives consolidate the modular library headers under
    # <archive>/boost instead of retaining the Git super-project's
    # libs/<name>/include layout expected by the modular CMake targets.
    add_subdirectory(
      ${playerbots_boost_SOURCE_DIR}
      ${playerbots_boost_BINARY_DIR}
      EXCLUDE_FROM_ALL)

  endif()

  # Boost's modular targets point at libs/<name>/include, a layout used by the
  # Git super-project. Release archives instead consolidate headers under
  # <archive>/boost. Apply this on every configure: after the first configure,
  # FetchContent sees the generated root CMakeLists and creates the targets
  # before the compatibility block above.
  set(_playerbots_boost_targets
    boost_assert
    boost_atomic
    boost_chrono
    boost_container
    boost_context
    boost_core
    boost_date_time
    boost_filesystem
    boost_stacktrace_basic
    boost_stacktrace_from_exception
    boost_stacktrace_noop
    boost_stacktrace_windbg
    boost_system
    boost_thread
    boost_unordered
    boost_variant2)
  foreach(_boost_target IN LISTS _playerbots_boost_targets)
    if(TARGET ${_boost_target})
      get_target_property(_boost_target_type ${_boost_target} TYPE)
      if(_boost_target_type STREQUAL "INTERFACE_LIBRARY")
        target_include_directories(${_boost_target} SYSTEM INTERFACE ${playerbots_boost_SOURCE_DIR})
      else()
        target_include_directories(${_boost_target} SYSTEM PUBLIC ${playerbots_boost_SOURCE_DIR})
      endif()
    endif()
  endforeach()
  target_include_directories(${LIBRARY_NAME} SYSTEM PRIVATE ${playerbots_boost_SOURCE_DIR})

  if(NOT TARGET Boost::thread OR NOT TARGET Boost::filesystem OR NOT TARGET Boost::system)
    message(FATAL_ERROR "Fetched Boost did not provide the required CMake targets")
  endif()
endif()

if(WIN32)
  # find_package(Boost) used to live in the else() branch alone, so on Windows
  # nothing ever located Boost. The only include path left was ${BOOST_ROOT}
  # from the top-level CMakeLists - the search hint, empty unless the builder
  # passes it - while botpch.h includes boost/algorithm/string.hpp
  # unconditionally, so the module could not compile at all.
  #
  # The same components as below: the module reaches for nine Boost libraries
  # and two of them, filesystem and thread, are compiled rather than
  # header-only. Windows linked neither, which would have failed at link time
  # once the headers were finally found.
  target_link_libraries(${LIBRARY_NAME}
    PRIVATE zlib
    PRIVATE ws2_32
    PRIVATE Boost::thread
    PRIVATE Boost::filesystem
    PRIVATE Boost::system
  )
else()
  target_link_libraries(${LIBRARY_NAME}
    PRIVATE ZLIB::ZLIB
    PRIVATE Boost::thread
    PRIVATE Boost::filesystem
    PRIVATE Boost::system
  )
endif()

target_include_directories(${LIBRARY_NAME}
  PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}
  PRIVATE ${CMAKE_SOURCE_DIR}/dep/include
  # include paths for transitive Penqle headers
  # (MapNodes/AbstractPlayer.h, Detour navmesh, framework Network).
  PRIVATE ${CMAKE_SOURCE_DIR}/src/game/MapNodes
  PRIVATE ${CMAKE_SOURCE_DIR}/dep/recastnavigation
  PRIVATE ${CMAKE_SOURCE_DIR}/src/framework/Network
)

# Install config files
#
# The expansion is chosen by project name, and vanilla is the default rather
# than a third named case: this project is called TurtleWoW, so none of the
# three names matched and aiplayerbot.conf.dist was never generated at all -
# on any platform. The install(FILES ...) below refers to it unconditionally,
# so cmake --install failed for everyone. It stayed hidden because the server
# is normally run straight out of the build tree.
if ( ${CMAKE_PROJECT_NAME} MATCHES "TBC")
	configure_file(${CMAKE_CURRENT_SOURCE_DIR}/playerbot/aiplayerbot.conf.dist.in.tbc ${CMAKE_CURRENT_BINARY_DIR}/aiplayerbot.conf.dist)
elseif ( ${CMAKE_PROJECT_NAME} MATCHES "WoTLK")
	configure_file(${CMAKE_CURRENT_SOURCE_DIR}/playerbot/aiplayerbot.conf.dist.in.wotlk ${CMAKE_CURRENT_BINARY_DIR}/aiplayerbot.conf.dist)
else()
	configure_file(${CMAKE_CURRENT_SOURCE_DIR}/playerbot/aiplayerbot.conf.dist.in ${CMAKE_CURRENT_BINARY_DIR}/aiplayerbot.conf.dist)
endif()
if (NOT CONF_INSTALL_DIR)
  set(CONF_INSTALL_DIR ${CONF_DIR})
endif()
install(FILES ${CMAKE_CURRENT_BINARY_DIR}/aiplayerbot.conf.dist DESTINATION ${CONF_INSTALL_DIR})

# AhBotConfig.cpp reads SYSCONFDIR"ahbot.conf", but the template was never
# generated or installed, so AHBot could not be switched on from a clean
# install at all - it just logs that it cannot open the file and stays off.
configure_file(${CMAKE_CURRENT_SOURCE_DIR}/ahbot/ahbot.conf.dist.in ${CMAKE_CURRENT_BINARY_DIR}/ahbot.conf.dist)
install(FILES ${CMAKE_CURRENT_BINARY_DIR}/ahbot.conf.dist DESTINATION ${CONF_INSTALL_DIR})

set_target_properties(${LIBRARY_NAME} PROPERTIES PROJECT_LABEL "PlayerBots")

option(PLAYERBOTS_BUILD_GATEWAY_TESTS "Build the standalone playerbot sidecar contract tests" OFF)
if(PLAYERBOTS_BUILD_GATEWAY_TESTS)
  add_executable(playerbot_dialogue_contract_tests
    ${CMAKE_CURRENT_SOURCE_DIR}/tests/PlayerbotDialogueContractTests.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/playerbot/PlayerbotDialogueContract.cpp)
  target_include_directories(playerbot_dialogue_contract_tests PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/playerbot
    ${CMAKE_SOURCE_DIR}/dep/include)
  set_target_properties(playerbot_dialogue_contract_tests PROPERTIES
    PROJECT_LABEL "PlayerBots Dialogue Contract Tests")
endif()

# Generate PCH
if(PCH)
  target_precompile_headers(${LIBRARY_NAME} PRIVATE ${bots_PCH})
endif()

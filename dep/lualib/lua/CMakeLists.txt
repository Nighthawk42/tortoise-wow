# Build recipe adapted from Eluna-Ports/Eluna-CMaNGOS-Classic (BSD-3-Clause).
# Lua itself is downloaded from lua.org and verified by its published SHA-256.
project(lua52 C)

include(FetchContent)
FetchContent_Declare(
  lua52
  URL https://www.lua.org/ftp/lua-5.2.4.tar.gz
  URL_HASH SHA256=b9e2e4aad6789b3b63a056d442f7b39f0ecfca3ae0f1fc0ae4e9614401b69f4b
  DOWNLOAD_EXTRACT_TIMESTAMP TRUE
)
FetchContent_MakeAvailable(lua52)

set(LUA_SOURCE_DIR "${lua52_SOURCE_DIR}/src")
file(GLOB LUA_HEADERS CONFIGURE_DEPENDS "${LUA_SOURCE_DIR}/*.h")
file(GLOB LUA_SOURCES CONFIGURE_DEPENDS "${LUA_SOURCE_DIR}/*.c")
list(REMOVE_ITEM LUA_SOURCES "${LUA_SOURCE_DIR}/lua.c" "${LUA_SOURCE_DIR}/luac.c")

add_library(lualib STATIC ${LUA_HEADERS} ${LUA_SOURCES})
set_target_properties(lualib PROPERTIES POSITION_INDEPENDENT_CODE ON LINKER_LANGUAGE C)
target_include_directories(lualib PUBLIC "${LUA_SOURCE_DIR}")

if(WIN32)
  target_compile_definitions(lualib PRIVATE _CRT_SECURE_NO_WARNINGS)
elseif(APPLE)
  target_compile_definitions(lualib PUBLIC LUA_USE_MACOSX)
  target_link_libraries(lualib PUBLIC ${CMAKE_DL_LIBS} m)
elseif(UNIX)
  target_compile_definitions(lualib PUBLIC LUA_USE_LINUX)
  target_link_libraries(lualib PUBLIC ${CMAKE_DL_LIBS} m)
endif()


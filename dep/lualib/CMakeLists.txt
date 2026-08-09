# Eluna targets Lua 5.2 by default. Keep the version fixed so every build uses
# the same language/runtime ABI.
set(LUA_VERSION "lua52" CACHE STRING "Lua version used by Eluna" FORCE)
set(LUA_STATIC ON CACHE BOOL "Link Lua statically" FORCE)

add_subdirectory(lua)


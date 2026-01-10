cmake_minimum_required (VERSION 3.2...3.14)
project (DiscordRPC)

include(GNUInstallDirs)

option(BUILD_EXAMPLES "Build example apps" OFF)
option(DISCORDRPC_ENABLE_CLANG_FORMAT OFF)

# format
file(GLOB_RECURSE ALL_SOURCE_FILES
    examples/*.cpp examples/*.h examples/*.c
    include/*.h
    src/*.cpp src/*.h src/*.c
)

if (DISCORDRPC_ENABLE_CLANG_FORMAT)
    # Set CLANG_FORMAT_SUFFIX if you are using custom clang-format, e.g. clang-format-5.0
    find_program(CLANG_FORMAT_CMD clang-format${CLANG_FORMAT_SUFFIX})

    if (CLANG_FORMAT_CMD)
        add_custom_target(
            clangformat
            COMMAND ${CLANG_FORMAT_CMD}
            -i -style=file -fallback-style=none
            ${ALL_SOURCE_FILES}
            DEPENDS
            ${ALL_SOURCE_FILES}
        )
    endif(CLANG_FORMAT_CMD)
endif(DISCORDRPC_ENABLE_CLANG_FORMAT)

# thirdparty stuff
find_file(RAPIDJSON NAMES rapidjson rapidjson-1.1.0 PATHS ${CMAKE_CURRENT_SOURCE_DIR}/thirdparty CMAKE_FIND_ROOT_PATH_BOTH)

# add subdirs

add_subdirectory(src)
if (BUILD_EXAMPLES)
    add_subdirectory(examples/send-presence)
endif(BUILD_EXAMPLES)

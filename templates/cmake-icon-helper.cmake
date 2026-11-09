# Drop this near the top of a Windows-capable CMakeLists, after the targets
# exist, and call it once per executable.
if(WIN32)
    function(moderngekko_add_executable_icon target icon_name)
        # Forward slashes: a native path in the generated .rc can turn \r, \n
        # or \t into control characters and break rc.exe.
        set(_moderngekko_icon_path
            "${CMAKE_CURRENT_SOURCE_DIR}/resources/icons/${icon_name}.ico")
        set(_moderngekko_icon_rc
            "${CMAKE_CURRENT_BINARY_DIR}/${target}-icon.rc")
        configure_file(
            "${CMAKE_CURRENT_SOURCE_DIR}/resources/icon.rc.in"
            "${_moderngekko_icon_rc}" @ONLY)
        target_sources(${target} PRIVATE "${_moderngekko_icon_rc}")
        set_source_files_properties("${_moderngekko_icon_rc}" PROPERTIES
            OBJECT_DEPENDS
            "${CMAKE_CURRENT_SOURCE_DIR}/resources/icons/${icon_name}.ico")
    endfunction()
endif()

# Example calls:
# add_executable(moderngekko-run ...)
# if(WIN32)
#     moderngekko_add_executable_icon(moderngekko-run game)
# endif()
#
# add_executable(moderngekko-launcher ...)
# if(WIN32)
#     moderngekko_add_executable_icon(moderngekko-launcher launcher)
# endif()

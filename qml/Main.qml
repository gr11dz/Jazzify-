import QtQuick
import QtQuick.Controls
import QtQuick.Window
import "components"
import "pages"
import "theme"

ApplicationWindow {
    id: window
    width: 1180
    height: 780
    minimumWidth: 900
    minimumHeight: 620
    visible: false
    title: "Jazzify"
    flags: Qt.Window
    color: compactNowPlaying ? "transparent" : Colors.background
    property bool nowPlayingOpen: false
    property bool compactNowPlaying: false
    property real normalWindowWidth: 1180
    property real normalWindowHeight: 780
    property real normalWindowX: 0
    property real normalWindowY: 0

    function updateWaveformState() {
        var normalFocused = window.visible && window.active && window.nowPlayingOpen
        var alwaysOn = settings.waveformAlwaysOn && window.nowPlayingOpen
        // Pinned visualizer mode is intentionally always live; the separate
        // overlay is specifically a desktop visualizer. The settings switch
        // additionally keeps waveform decoding alive while Now Playing is
        // open even when the main window is not focused.
        var overlayActive = window.compactNowPlaying && overlay.visible && window.nowPlayingOpen
        var enabled = normalFocused || alwaysOn || overlayActive

        player.setWaveformEnabled(enabled)

        if (stack.currentItem && stack.currentItem.hasOwnProperty("waveformActive"))
            stack.currentItem.waveformActive = normalFocused || alwaysOn

        overlayNowPlaying.waveformActive = overlayActive || alwaysOn
    }

    onActiveChanged: updateWaveformState()
    onVisibleChanged: updateWaveformState()
    onNowPlayingOpenChanged: updateWaveformState()
    Connections {
        target: settings
        function onWaveformAlwaysOnChanged() {
            window.updateWaveformState()
        }
    }

    function enterCompactNowPlaying() {
        // Keep the overlay hidden while its compact UI is initialized so no
        // intermediate full-UI frame can flash before the window is shown.
        overlay.visible = false
        overlayNowPlaying.compactMode = true
        compactNowPlaying = true

        // Use a dedicated transparent top-level overlay window. Keeping the
        // normal application window opaque avoids Windows compositor issues
        // with QML ApplicationWindow backgrounds.
        overlay.width = 420
        overlay.height = 420

        var centerX = window.x + Math.round((window.width - overlay.width) / 2)
        var centerY = window.y + Math.round((window.height - overlay.height) / 2)

        overlay.x = Math.max(0, centerX)
        overlay.y = Math.max(0, centerY)

        // Keep the owner window alive. On Windows, hiding the owner can also
        // hide a Qt.Tool child window, which made the entire app appear to
        // disappear. Move the owner off-screen and make it effectively
        // invisible instead. The transparent overlay remains independently
        // visible on top.
        normalWindowX = window.x
        normalWindowY = window.y
        normalWindowWidth = window.width
        normalWindowHeight = window.height

        window.opacity = 0.0
        window.x = -32000
        window.y = -32000
        window.width = 1
        window.height = 1
        window.visible = true

        overlay.visible = true
        overlay.raise()
        overlay.requestActivate()

        Qt.callLater(function() {
            window.updateWaveformState()
        })
    }

    function exitCompactNowPlaying() {
        if (!compactNowPlaying)
            return

        compactNowPlaying = false
        overlayNowPlaying.compactMode = true

        overlay.hide()

        window.width = normalWindowWidth
        window.height = normalWindowHeight
        window.x = normalWindowX
        window.y = normalWindowY
        window.opacity = 1.0
        window.visible = true
        window.raise()
        window.requestActivate()

        Qt.callLater(function() {
            window.updateWaveformState()
            window.requestUpdate()
        })
    }

    StackView {
        id: stack
        anchors.fill: parent
        anchors.bottomMargin: (player.path !== "" && !window.nowPlayingOpen) ? 82 : 0
        initialItem: songsPage
        clip: true
    }

    Component {
        id: songsPage
        Songs { onOpenSettingsRequested: stack.push(settingsPage) }
    }

    Component {
        id: settingsPage
        Settings { onBackRequested: stack.pop() }
    }

    Component {
        id: nowPlayingPage
        NowPlaying {
            hostWindow: window
            onBackRequested: {
                // Back from the normal Now Playing page should only close the
                // page. Exiting compact mode is only valid when we are actually
                // in the pinned overlay. Calling exitCompactNowPlaying() here
                // during normal navigation was restoring/saving window geometry
                // as though the app were pinned, which could move the window to
                // the top-left corner until it was resized.
                if (window.compactNowPlaying)
                    window.exitCompactNowPlaying()

                window.nowPlayingOpen = false
                stack.pop()
                updateWaveformState()
            }

            onCompactModeRequested: function(enabled) {
                if (enabled)
                    window.enterCompactNowPlaying()
                else
                    window.exitCompactNowPlaying()
            }
        }
    }

    Window {
        id: overlay
        objectName: "overlayWindow"

        visible: false
        width: 420
        height: 420
        color: "transparent"
        opacity: 1.0
        flags: Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool | Qt.NoDropShadowWindowHint
        modality: Qt.NonModal


        // The overlay is intentionally outside the normal ApplicationWindow
        // so the compositor sees a genuinely transparent top-level surface.
        // The shared default QSurfaceFormat is configured for alpha in app.py.

        NowPlaying {
            id: overlayNowPlaying
            hostWindow: overlay
            anchors.fill: parent
            compactMode: true
            waveformActive: overlay.visible && overlay.active
            onCompactModeRequested: function(enabled) {
                if (!enabled)
                    window.exitCompactNowPlaying()
            }
            onBackRequested: {
                window.exitCompactNowPlaying()
            }
        }

        onActiveChanged: window.updateWaveformState()
    }

    Component.onCompleted: updateWaveformState()

    Rectangle {
        id: libraryLoadingOverlay
        visible: library.indexing
        anchors.fill: parent
        color: Qt.rgba(Colors.background.r, Colors.background.g, Colors.background.b, 0.94)
        z: 1000

        MouseArea {
            anchors.fill: parent
            acceptedButtons: Qt.AllButtons
        }

        Column {
            anchors.centerIn: parent
            width: Math.min(parent.width - 80, 440)
            spacing: 18

            BusyIndicator {
                anchors.horizontalCenter: parent.horizontalCenter
                running: library.indexing
                width: 54
                height: 54
            }

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: "Loading music library"
                color: Colors.text
                font.pixelSize: 21
                font.weight: Font.DemiBold
            }

            Text {
                width: parent.width
                text: "Jazzify is scanning your music folder and building the library. You can keep this window open while the indexing finishes."
                color: Colors.muted
                font.pixelSize: 12
                wrapMode: Text.WordWrap
                horizontalAlignment: Text.AlignHCenter
            }
        }
    }

    Text {
        visible: player.error !== ""
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: miniPlayer.top
        anchors.bottomMargin: 6
        text: player.error
        color: "#FF6B6B"
        font.pixelSize: 11
        elide: Text.ElideRight
        width: Math.min(parent.width - 40, 800)
        horizontalAlignment: Text.AlignHCenter
        z: 10
    }

    Rectangle {
        id: miniPlayer
        visible: player.path !== "" && !window.nowPlayingOpen
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        height: 82
        color: Qt.darker(player.backgroundColor, 1.15)
        border.color: Qt.rgba(1,1,1,0.06)
        border.width: 1

        Behavior on color { ColorAnimation { duration: 500 } }

        MouseArea {
            anchors.fill: parent
            z: 0
            onClicked: {
                window.nowPlayingOpen = true
                stack.push(nowPlayingPage)
                updateWaveformState()
            }
        }

        Row {
            anchors.fill: parent
            anchors.margins: 12
            spacing: 12
            z: 1

            Rectangle {
                width: 58; height: 58; radius: 11
                anchors.verticalCenter: parent.verticalCenter
                color: Colors.surface3
                clip: true
                Image {
                    anchors.fill: parent
                    source: player.artwork ? "file:///" + player.artwork.replace(/\\/g, "/") : ""
                    fillMode: Image.PreserveAspectCrop
                    asynchronous: true
                    cache: true
                }
            }

            Column {
                width: 300
                anchors.verticalCenter: parent.verticalCenter
                spacing: 3
                Text { width: parent.width; text: player.title || "Nothing playing"; color: Colors.text; font.pixelSize: 14; font.weight: Font.DemiBold; elide: Text.ElideRight }
                Text { width: parent.width; text: player.artist || ""; color: Colors.muted; font.pixelSize: 12; elide: Text.ElideRight }
            }

            Item { width: Math.max(0, miniPlayer.width - 500); height: 1 }

            ControlIcon {
                width: 48; height: 48
                anchors.verticalCenter: parent.verticalCenter
                iconSource: player.playing ? Qt.resolvedUrl("../images/pause.png") : Qt.resolvedUrl("../images/play.png")
                fallback: player.playing ? "Ⅱ" : "▶"
                surfaceColor: Qt.hsla(
                    player.primaryColor.hslHue < 0 ? 0 : player.primaryColor.hslHue,
                    Math.max(0.18, Math.min(0.48, player.primaryColor.hslSaturation)),
                    0.93,
                    1.0
                )
                hoverSurfaceColor: "#FFFFFF"
                pressedSurfaceColor: "#E9E9EE"
                onClicked: {
                    if (player.playing)
                        player.pause()
                    else
                        player.play()
                }
            }
        }

        Rectangle {
            anchors.left: parent.left
            anchors.bottom: parent.bottom
            width: parent.width * (player.duration > 0 ? player.position / player.duration : 0)
            height: 2
            color: player.primaryColor
            Behavior on color { ColorAnimation { duration: 400 } }
        }
    }
}

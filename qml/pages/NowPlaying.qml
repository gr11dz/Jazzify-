import QtQuick
import QtQuick.Controls
import Qt5Compat.GraphicalEffects
import "../theme"
import "../components"

Item {
    id: root
    signal backRequested()
    signal compactModeRequested(bool enabled)

    // Main.qml keeps this true only while Now Playing is open AND the
    // application has focus. This preserves the CPU-saving behavior.
    property bool waveformActive: false
    property bool compactMode: false
    property bool queueOpen: false
    property var hostWindow: null

    readonly property color pageBackground: player.backgroundColor
    readonly property color primary: player.primaryColor
    readonly property color secondary: player.secondaryColor

    function clamp(value, minimum, maximum) {
        return Math.max(minimum, Math.min(maximum, value))
    }

    function blend(c1, c2, amount) {
        return Qt.rgba(
            c1.r * (1 - amount) + c2.r * amount,
            c1.g * (1 - amount) + c2.g * amount,
            c1.b * (1 - amount) + c2.b * amount,
            1
        )
    }

    function contrastingWaveColor(base) {
        var hue = base.hslHue
        if (hue < 0)
            hue = 0

        hue = (hue + 0.5) % 1.0

        var saturation = Math.max(
            0.62,
            Math.min(0.95, base.hslSaturation + 0.25)
        )

        var lightness = base.hslLightness < 0.5 ? 0.84 : 0.20

        return Qt.hsla(
            hue,
            saturation,
            lightness,
            1
        )
    }

    readonly property color waveformColor:
        root.contrastingWaveColor(root.primary)

    readonly property real themeHue:
        root.primary.hslHue < 0 ? 0 : root.primary.hslHue

    readonly property real themeSaturation:
        Math.max(
            0.18,
            Math.min(0.48, root.primary.hslSaturation)
        )

    readonly property color iconSurface:
        Qt.hsla(
            root.themeHue,
            root.themeSaturation,
            0.93,
            1
        )

    readonly property color iconSurfaceHover:
        Qt.hsla(
            root.themeHue,
            Math.min(0.55, root.themeSaturation + 0.05),
            0.98,
            1
        )

    readonly property color iconBorder:
        Qt.hsla(
            root.themeHue,
            Math.min(0.70, root.themeSaturation + 0.16),
            0.54,
            0.74
        )

    readonly property color iconPressed:
        Qt.hsla(
            root.themeHue,
            root.themeSaturation,
            0.86,
            1
        )

    // ------------------------------------------------------------
    // BACKGROUND
    // ------------------------------------------------------------

    Rectangle {
        visible: !root.compactMode
        anchors.fill: parent
        color: root.pageBackground

        Behavior on color {
            ColorAnimation {
                duration: 900
                easing.type: Easing.InOutCubic
            }
        }
    }

    // Oversized album artwork creates the ambient color field.
    // It is deliberately subtle: the primary/secondary colors remain the
    // real theme drivers, while this layer gives the page a more cinematic feel.
    Image {
        visible: !root.compactMode
        anchors.fill: parent
        source: player.artwork
            ? "file:///" + player.artwork.replace(/\\/g, "/")
            : ""
        fillMode: Image.PreserveAspectCrop
        asynchronous: true
        cache: true
        opacity: status === Image.Ready ? 0.10 : 0
        scale: 1.14

        Behavior on opacity {
            NumberAnimation { duration: 650; easing.type: Easing.InOutCubic }
        }

        Behavior on scale {
            NumberAnimation { duration: 900; easing.type: Easing.InOutSine }
        }
    }

    // Primary color atmosphere.
    Rectangle {
        visible: !root.compactMode
        width: Math.max(parent.width * 0.92, 760)
        height: width
        x: -width * 0.40
        y: -width * 0.58
        radius: width / 2
        color: root.primary
        opacity: player.playing ? 0.22 : 0.16
        scale: player.playing ? 1.08 : 1.0

        Behavior on color { ColorAnimation { duration: 850 } }
        Behavior on opacity { NumberAnimation { duration: 650 } }
        Behavior on scale {
            NumberAnimation {
                duration: 1150
                easing.type: Easing.InOutSine
            }
        }
    }

    // Secondary color atmosphere.
    Rectangle {
        visible: !root.compactMode
        width: Math.max(parent.width * 0.78, 620)
        height: width
        x: parent.width - width * 0.38
        y: parent.height - width * 0.72
        radius: width / 2
        color: root.secondary
        opacity: player.playing ? 0.20 : 0.14
        scale: player.playing ? 1.06 : 1.0

        Behavior on color { ColorAnimation { duration: 900 } }
        Behavior on opacity { NumberAnimation { duration: 650 } }
        Behavior on scale {
            NumberAnimation {
                duration: 1250
                easing.type: Easing.InOutSine
            }
        }
    }

    // Contrast wash so text and controls remain readable.
    Rectangle {
        visible: !root.compactMode
        anchors.fill: parent
        color: "transparent"

        gradient: Gradient {
            GradientStop {
                position: 0.0
                color: Qt.rgba(255, 255, 255, 0.015)
            }
            GradientStop {
                position: 0.48
                color: Qt.rgba(0, 0, 0, 0.05)
            }
            GradientStop {
                position: 1.0
                color: Qt.rgba(0, 0, 0, 0.30)
            }
        }
    }

    // A subtle animated halo follows the album theme while playing.
    Rectangle {
        visible: !root.compactMode
        anchors.centerIn: parent
        width: Math.min(parent.width, parent.height) * 0.88
        height: width
        radius: width / 2
        color: "transparent"
        border.color: root.primary
        border.width: 1
        opacity: player.playing ? 0.11 : 0.05
        scale: player.playing ? 1.035 : 0.985

        Behavior on border.color { ColorAnimation { duration: 800 } }
        Behavior on opacity { NumberAnimation { duration: 600 } }
        Behavior on scale {
            NumberAnimation {
                duration: 1200
                easing.type: Easing.InOutSine
            }
        }
    }

    Rectangle {
        visible: !root.compactMode
        anchors.fill: parent
        color: "transparent"
        border.color: Qt.rgba(255, 255, 255, 0.04)
        border.width: 1
    }

    // ------------------------------------------------------------
    // TOP BAR
    // ------------------------------------------------------------

    ControlIcon {
        id: backButton
        visible: !root.compactMode
        x: 18
        y: 14
        width: 42
        height: 42
        iconSource: Qt.resolvedUrl("../../images/back.png")
        fallback: "←"
        surfaceColor: root.iconSurface
        hoverSurfaceColor: root.iconSurfaceHover
        pressedSurfaceColor: root.iconPressed
        borderColor: root.iconBorder
        onClicked: root.backRequested()
    }

    Text {
        visible: !root.compactMode
        anchors.top: parent.top
        anchors.topMargin: 20
        anchors.horizontalCenter: parent.horizontalCenter
        text: "NOW PLAYING"
        color: Qt.rgba(1, 1, 1, 0.66)
        font.pixelSize: 10
        font.letterSpacing: 3.2
    }

    // ------------------------------------------------------------
    // CENTER STAGE
    // ------------------------------------------------------------

    Item {
        id: stage
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.bottom: transportDock.top
        anchors.topMargin: 42
        anchors.bottomMargin: 8

        // Circular waveform. It is intentionally generated only when
        // waveformActive is true; Main.qml disables the audio analysis when
        // Jazzify loses focus.
        Item {
            id: waveformRing
            anchors.centerIn: parent
            width: Math.min(
                parent.width * (root.compactMode ? 0.92 : 0.56),
                parent.height * (root.compactMode ? 0.92 : 0.66),
                root.compactMode ? 380 : 430
            )
            height: width
            visible: root.waveformActive || ringFade.opacity > 0
            opacity: root.waveformActive ? 1 : 0
            scale: root.waveformActive ? 1.0 : 0.94

            Behavior on opacity {
                NumberAnimation {
                    duration: 360
                    easing.type: Easing.InOutCubic
                }
            }

            Behavior on scale {
                NumberAnimation {
                    duration: 430
                    easing.type: Easing.OutCubic
                }
            }

            Rectangle {
                id: ringFade
                anchors.fill: parent
                color: "transparent"
                opacity: 0
            }

            // Soft outer ring.
            Rectangle {
                anchors.fill: parent
                radius: width / 2
                color: "transparent"
                border.color: root.primary
                border.width: 2
                opacity: player.playing ? 0.30 : 0.18

                Behavior on border.color {
                    ColorAnimation { duration: 650 }
                }

                Behavior on opacity {
                    NumberAnimation { duration: 450 }
                }
            }

            // Secondary thin ring.
            Rectangle {
                anchors.centerIn: parent
                width: parent.width - 28
                height: width
                radius: width / 2
                color: "transparent"
                border.color: root.secondary
                border.width: 1
                opacity: player.playing ? 0.35 : 0.20

                Behavior on border.color {
                    ColorAnimation { duration: 700 }
                }
            }

            // Dense audio-responsive bars radiating OUTWARD from the album.
            // The inner edge stays near the album while the waveform grows toward
            // the outside of the ring. More bars are rendered while focused because
            // waveform decoding/updates are disabled when Jazzify loses focus.
            Repeater {
                model: root.waveformActive ? 144 : 0

                delegate: Item {
                    width: waveformRing.width
                    height: waveformRing.height
                    rotation: index * (360 / 144)

                    Rectangle {
                        id: radialBar

                        property real amplitude: player.waveform.length > 0
                            ? player.waveform[index % player.waveform.length]
                            : 0.02

                        width: 2.4
                        height: 10 + (amplitude * 72)
                        radius: width / 2

                        x: (parent.width - width) / 2

                        // Start at the album's outer edge and grow outward.
                        // QML coordinates increase downward, so the bar is placed
                        // above the center by its full radial length.
                        y: (parent.height / 2)
                           - (coverFrame.width / 2)
                           - 18
                           - height

                        color: root.waveformColor
                        opacity: 0.94

                        Behavior on height {
                            NumberAnimation {
                                duration: 75
                                easing.type: Easing.OutCubic
                            }
                        }

                        Behavior on color {
                            ColorAnimation { duration: 450 }
                        }
                    }
                }
            }
        }

        // Album cover sits inside the waveform ring.
        Rectangle {
            id: coverFrame
            anchors.centerIn: parent
            width: Math.min(
                parent.width * (root.compactMode ? 0.60 : 0.34),
                parent.height * (root.compactMode ? 0.60 : 0.48),
                root.compactMode ? 250 : 280
            )
            height: width
            radius: width / 2
            color: "transparent"
            // Keep the album edge distinct without inheriting a bright/white
            // primary color from light artwork. The waveform color is already
            // chosen for strong contrast against the album palette.
            // The waveform already provides the visual edge around the artwork.
            // Do not draw a circular border here: bright album palettes can make
            // the border look like an unwanted white ring.
            border.width: 0
            scale: player.playing ? 1.01 : 1.0

            Behavior on border.color {
                ColorAnimation { duration: 650 }
            }

            Behavior on scale {
                NumberAnimation {
                    duration: 650
                    easing.type: Easing.InOutSine
                }
            }



            // Render the artwork inside a dedicated masked item.  This avoids
            // the rectangular Image texture leaking through the circular frame.
            Item {
                id: coverMaskItem
                anchors.fill: parent
                clip: true
                layer.enabled: true
                layer.effect: OpacityMask {
                    maskSource: Rectangle {
                        width: coverMaskItem.width
                        height: coverMaskItem.height
                        radius: Math.min(width, height) / 2
                        color: "white"
                    }
                }

                Image {
                    id: coverImage
                    anchors.fill: parent
                    source: player.artwork
                        ? "file:///" + player.artwork.replace(/\\/g, "/")
                        : ""
                    fillMode: Image.PreserveAspectCrop
                    asynchronous: true
                    cache: true
                    mipmap: true
                    visible: status === Image.Ready
                    opacity: status === Image.Ready ? 1 : 0
                    smooth: true

                    Behavior on opacity {
                        NumberAnimation { duration: 300 }
                    }
                }
            }

            Text {
                anchors.centerIn: parent
                text: "♪"
                color: Qt.rgba(1, 1, 1, 0.38)
                font.pixelSize: 54
                visible: player.artwork === ""
            }
        }

        // --------------------------------------------------------
        // METADATA IN THE OLD WAVEFORM AREA
        // --------------------------------------------------------

        Column {
            visible: !root.compactMode
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.bottom: parent.bottom
            anchors.bottomMargin: 2
            width: Math.min(parent.width - 90, 650)
            spacing: 2

            Text {
                width: parent.width
                text: player.title || "Nothing playing"
                color: Colors.text
                font.pixelSize: 25
                font.weight: Font.DemiBold
                horizontalAlignment: Text.AlignHCenter
                elide: Text.ElideRight
            }

            Text {
                width: parent.width
                text: player.artist || ""
                color: Qt.rgba(1, 1, 1, 0.82)
                font.pixelSize: 14
                horizontalAlignment: Text.AlignHCenter
                elide: Text.ElideRight
            }

            Text {
                width: parent.width
                text: player.album || ""
                color: Qt.rgba(1, 1, 1, 0.53)
                font.pixelSize: 11
                horizontalAlignment: Text.AlignHCenter
                elide: Text.ElideRight
            }
        }
    }

    // ------------------------------------------------------------
    // COMPACT / PIN MODE
    // ------------------------------------------------------------

    ControlIcon {
        id: compactButton
        visible: !root.compactMode
        anchors.left: parent.left
        anchors.bottom: parent.bottom
        anchors.leftMargin: 16
        anchors.bottomMargin: 14
        width: 44
        height: 44
        iconSource: Qt.resolvedUrl("../../images/pin.png")
        fallback: "📌"
        surfaceColor: root.iconSurface
        hoverSurfaceColor: root.iconSurfaceHover
        pressedSurfaceColor: root.iconPressed
        borderColor: root.iconBorder
        onClicked: { root.compactMode = true; root.compactModeRequested(true) }
    }

    ControlIcon {
        id: queueButton
        visible: !root.compactMode
        anchors.left: compactButton.right
        anchors.bottom: parent.bottom
        anchors.leftMargin: 10
        anchors.bottomMargin: 14
        width: 44
        height: 44
        iconSource: Qt.resolvedUrl("../../images/list.png")
        fallback: "☷"
        surfaceColor: root.iconSurface
        hoverSurfaceColor: root.iconSurfaceHover
        pressedSurfaceColor: root.iconPressed
        borderColor: root.iconBorder
        active: root.queueOpen
        activeSurfaceColor: root.blend(root.iconSurface, root.iconSurfaceHover, 0.5)
        activeBorderColor: root.primary
        onClicked: root.queueOpen = !root.queueOpen
    }

    // ------------------------------------------------------------
    // UPCOMING QUEUE SIDEBAR
    // ------------------------------------------------------------

    Rectangle {
        id: queueBackdrop
        anchors.fill: parent
        visible: root.queueOpen && !root.compactMode
        z: 30
        color: Qt.rgba(0, 0, 0, 0.28)

        MouseArea {
            anchors.fill: parent
            onClicked: root.queueOpen = false
        }
    }

    Rectangle {
        id: queueSidebar
        property real targetX: root.queueOpen && !root.compactMode
            ? parent.width - width
            : parent.width

        width: Math.min(390, parent.width * 0.38)
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        x: targetX
        z: 31

        color: Qt.rgba(
            root.pageBackground.r * 0.92,
            root.pageBackground.g * 0.92,
            root.pageBackground.b * 0.92,
            0.98
        )

        border.color: Qt.rgba(1, 1, 1, 0.08)
        border.width: 1

        Behavior on x {
            NumberAnimation {
                duration: 340
                easing.type: Easing.OutCubic
            }
        }

        Column {
            anchors.fill: parent
            anchors.margins: 18
            spacing: 12

            Row {
                width: parent.width
                height: 42
                spacing: 10

                Column {
                    width: parent.width - 52
                    spacing: 2

                    Text {
                        text: "UP NEXT"
                        color: Colors.text
                        font.pixelSize: 14
                        font.weight: Font.DemiBold
                    }

                    Text {
                        text: player.queueItems.length + " song" + (player.queueItems.length === 1 ? "" : "s")
                        color: Colors.muted
                        font.pixelSize: 11
                    }
                }

                ControlIcon {
                    width: 40
                    height: 40
                    iconSource: ""
                    fallback: "×"
                    surfaceColor: root.iconSurface
                    hoverSurfaceColor: root.iconSurfaceHover
                    pressedSurfaceColor: root.iconPressed
                    borderColor: root.iconBorder
                    onClicked: root.queueOpen = false
                }
            }

            Rectangle {
                width: parent.width
                height: 1
                color: Qt.rgba(1, 1, 1, 0.07)
            }

            ListView {
                id: queueList
                width: parent.width
                height: parent.height - 66
                clip: true
                spacing: 8
                boundsBehavior: Flickable.StopAtBounds
                model: player.queueItems

                delegate: Item {
                    id: queueItem

                    width: queueList.width
                    height: 66

                    property real dragX: dragHandler.translation.x
                    property real dragY: dragHandler.translation.y
                    property bool removing: dragX < -55

                    transform: Translate {
                        x: dragHandler.active ? dragHandler.translation.x : 0
                        y: dragHandler.active ? dragHandler.translation.y : 0
                    }

                    z: dragHandler.active ? 100 : 1

                    Rectangle {
                        anchors.fill: parent
                        radius: 14
                        color: queueItem.removing
                            ? Qt.rgba(0.95, 0.20, 0.20, 0.18)
                            : Qt.rgba(1, 1, 1, 0.045)
                        border.color: queueItem.removing
                            ? Qt.rgba(1, 0.35, 0.35, 0.72)
                            : Qt.rgba(1, 1, 1, 0.06)
                        border.width: 1

                        Behavior on color { ColorAnimation { duration: 120 } }
                        Behavior on border.color { ColorAnimation { duration: 120 } }
                    }

                    Rectangle {
                        id: queueArtworkFrame
                        x: 10
                        y: 8
                        width: 50
                        height: 50
                        radius: 10
                        color: Qt.rgba(1,1,1,0.05)
                        clip: true

                        Image {
                            anchors.fill: parent
                            source: modelData.artwork
                                ? "file:///" + modelData.artwork.replace(/\\/g, "/")
                                : ""
                            fillMode: Image.PreserveAspectCrop
                            asynchronous: true
                            cache: true
                            visible: status === Image.Ready
                        }
                    }

                    Column {
                        x: 72
                        y: 14
                        width: parent.width - 94
                        spacing: 2

                        Text {
                            width: parent.width
                            text: modelData.title
                            color: Colors.text
                            font.pixelSize: 12
                            font.weight: Font.DemiBold
                            elide: Text.ElideRight
                        }

                        Text {
                            width: parent.width
                            text: modelData.artist + (modelData.album ? " • " + modelData.album : "")
                            color: Colors.muted
                            font.pixelSize: 10
                            elide: Text.ElideRight
                        }
                    }

                    Text {
                        visible: queueItem.removing
                        anchors.right: parent.right
                        anchors.rightMargin: 14
                        anchors.verticalCenter: parent.verticalCenter
                        text: "REMOVE"
                        color: Qt.rgba(1, 0.52, 0.52, 0.92)
                        font.pixelSize: 9
                        font.weight: Font.DemiBold
                    }

                    DragHandler {
                        id: dragHandler
                        target: null
                        xAxis.enabled: true
                        yAxis.enabled: true
                        onActiveChanged: {
                            if (active)
                                return

                            if (queueItem.dragX < -65) {
                                player.removeQueueItem(modelData.displayIndex)
                                return
                            }

                            var targetIndex = modelData.displayIndex
                                + Math.round(queueItem.dragY / queueItem.height)
                            targetIndex = Math.max(0, Math.min(player.queueItems.length - 1, targetIndex))

                            if (targetIndex !== modelData.displayIndex)
                                player.moveQueueItem(modelData.displayIndex, targetIndex)
                        }
                    }

                    MouseArea {
                        anchors.fill: parent
                        enabled: !dragHandler.active
                        onDoubleClicked: {
                            var index = modelData.displayIndex
                            var items = player.queueItems
                            if (index >= 0 && index < items.length)
                                player.playQueueItem(index)
                        }
                    }

                    Behavior on opacity { NumberAnimation { duration: 180 } }
                }
            }
        }
    }

    // In pinned mode the whole transparent overlay is draggable. Double-click
    // anywhere on it exits pinned mode.
    MouseArea {
        id: compactOverlayMouse
        anchors.fill: parent
        visible: root.compactMode
        z: 20
        cursorShape: Qt.SizeAllCursor

        // Use the native window drag operation instead of moving the window
        // manually from QML. This keeps the overlay smooth and prevents
        // coordinate jitter when Windows compositing is involved.
        onPressed: function(mouse) {
            if (root.hostWindow && root.hostWindow.startSystemMove)
                root.hostWindow.startSystemMove()
        }

        onDoubleClicked: {
            root.compactMode = false
            root.compactModeRequested(false)
        }
    }

    // ------------------------------------------------------------
    // TRANSPORT DOCK
    // ------------------------------------------------------------

    Rectangle {
        id: transportDock
        visible: !root.compactMode
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        height: 154
        color: Qt.rgba(
            root.primary.r * 0.10,
            root.primary.g * 0.10,
            root.primary.b * 0.10,
            0.24
        )
        border.color: Qt.rgba(1, 1, 1, 0.09)
        border.width: 1

        Behavior on color {
            ColorAnimation { duration: 650 }
        }

        Column {
            anchors.fill: parent
            anchors.leftMargin: 16
            anchors.rightMargin: 16
            anchors.topMargin: 10
            anchors.bottomMargin: 10
            spacing: 7

            // Progress
            Item {
                width: parent.width
                height: 24

                Slider {
                    id: progressSlider
                    anchors.fill: parent
                    from: 0
                    to: Math.max(1, player.duration)
                    value: player.position
                    onMoved: player.seek(value)

                    Connections {
                        target: player

                        function onPositionChanged(position) {
                            if (!progressSlider.pressed)
                                progressSlider.value = position
                        }

                        function onDurationChanged(duration) {
                            if (!progressSlider.pressed)
                                progressSlider.value = player.position
                        }
                    }

                    background: Rectangle {
                        x: progressSlider.leftPadding
                        y: progressSlider.topPadding + progressSlider.availableHeight / 2 - height / 2
                        width: progressSlider.availableWidth
                        height: 6
                        radius: 3
                        color: Qt.rgba(1, 1, 1, 0.19)

                        Rectangle {
                            width: progressSlider.visualPosition * parent.width
                            height: parent.height
                            radius: 3
                            color: root.primary
                        }
                    }

                    handle: Item {
                        implicitWidth: 1
                        implicitHeight: 1
                        width: 1
                        height: 1
                    }
                }

                Rectangle {
                    width: 14
                    height: 14
                    radius: 7
                    x: progressSlider.leftPadding + progressSlider.visualPosition * progressSlider.availableWidth - width / 2
                    y: progressSlider.topPadding + progressSlider.availableHeight / 2 - height / 2
                    color: root.iconSurface
                    border.color: root.primary
                    border.width: 2
                }
            }

            Row {
                width: parent.width
                Text {
                    text: formatTime(player.position)
                    color: Colors.muted
                    font.pixelSize: 9
                }
                Item {
                    width: parent.width - 78
                    height: 1
                }
                Text {
                    text: formatTime(player.duration)
                    color: Colors.muted
                    font.pixelSize: 9
                }
            }

            Row {
                anchors.horizontalCenter: parent.horizontalCenter
                spacing: 10
                height: 48

                ControlIcon {
                    width: 42; height: 42
                    iconSource: Qt.resolvedUrl("../../images/repeat.png")
                    fallback: "↻"
                    active: player.repeatMode !== 0
                    badgeText: player.repeatMode === 2 ? "1" : ""
                    surfaceColor: root.iconSurface
                    hoverSurfaceColor: root.iconSurfaceHover
                    pressedSurfaceColor: root.iconPressed
                    activeSurfaceColor: root.blend(root.iconSurface, root.iconSurfaceHover, 0.5)
                    borderColor: root.iconBorder
                    activeBorderColor: root.primary
                    onClicked: player.toggleRepeat()
                }

                ControlIcon {
                    width: 42; height: 42
                    iconSource: Qt.resolvedUrl("../../images/previous.png")
                    fallback: "⏮"
                    surfaceColor: root.iconSurface
                    hoverSurfaceColor: root.iconSurfaceHover
                    pressedSurfaceColor: root.iconPressed
                    borderColor: root.iconBorder
                    onClicked: player.previous()
                }

                ControlIcon {
                    width: 50; height: 50
                    iconSource: player.playing
                        ? Qt.resolvedUrl("../../images/pause.png")
                        : Qt.resolvedUrl("../../images/play.png")
                    fallback: player.playing ? "Ⅱ" : "▶"
                    surfaceColor: root.iconSurface
                    hoverSurfaceColor: root.iconSurfaceHover
                    pressedSurfaceColor: root.iconPressed
                    borderColor: root.iconBorder
                    onClicked: player.togglePlayback()
                }

                ControlIcon {
                    width: 42; height: 42
                    iconSource: Qt.resolvedUrl("../../images/next.png")
                    fallback: "⏭"
                    surfaceColor: root.iconSurface
                    hoverSurfaceColor: root.iconSurfaceHover
                    pressedSurfaceColor: root.iconPressed
                    borderColor: root.iconBorder
                    onClicked: player.next()
                }

                ControlIcon {
                    width: 42; height: 42
                    iconSource: Qt.resolvedUrl("../../images/shuffle.png")
                    fallback: "⇄"
                    active: player.shuffle
                    badgeText: player.shuffle ? "✓" : ""
                    surfaceColor: root.iconSurface
                    hoverSurfaceColor: root.iconSurfaceHover
                    pressedSurfaceColor: root.iconPressed
                    activeSurfaceColor: root.blend(root.iconSurface, root.iconSurfaceHover, 0.5)
                    borderColor: root.iconBorder
                    activeBorderColor: root.primary
                    onClicked: player.toggleShuffle()
                }
            }
        }
    }

    function formatTime(milliseconds) {
        if (milliseconds <= 0)
            return "0:00"

        let seconds = Math.floor(milliseconds / 1000)
        let minutes = Math.floor(seconds / 60)
        seconds = seconds % 60

        return minutes + ":" + (seconds < 10 ? "0" : "") + seconds
    }
}

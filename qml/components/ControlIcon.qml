import QtQuick

Item {
    id: root

    signal clicked()

    property string iconSource: ""
    property string fallback: ""
    property bool circular: true
    property bool active: false
    property string badgeText: ""
    property color surfaceColor: "#F4F4F6"
    property color hoverSurfaceColor: "#FFFFFF"
    property color pressedSurfaceColor: "#E9E9EE"
    property color activeSurfaceColor: "#EEF2FF"
    property color borderColor: "transparent"
    property color activeBorderColor: borderColor
    property bool hovered: mouseArea.containsMouse
    property bool down: mouseArea.pressed

    scale: mouseArea.pressed ? 0.94 : 1.0

    Behavior on scale {
        NumberAnimation {
            duration: 90
            easing.type: Easing.OutCubic
        }
    }

    Rectangle {
        id: surface
        anchors.fill: parent
        radius: root.circular ? width / 2 : 12

        color: root.active
            ? root.activeSurfaceColor
            : root.down
                ? root.pressedSurfaceColor
                : root.hovered
                    ? root.hoverSurfaceColor
                    : root.surfaceColor

        opacity: 0.99

        border.color: root.active ? root.activeBorderColor : root.borderColor
        border.width: root.active ? 2.5 : ((root.borderColor.a > 0) ? 1.5 : 0)

        Behavior on color {
            ColorAnimation {
                duration: 140
                easing.type: Easing.OutCubic
            }
        }

        Behavior on border.color {
            ColorAnimation { duration: 180 }
        }

        Image {
            id: icon
            anchors.fill: parent
            anchors.margins: Math.max(
                8,
                Math.round(Math.min(parent.width, parent.height) * 0.24)
            )
            source: root.iconSource
            fillMode: Image.PreserveAspectFit
            smooth: true
            mipmap: true
            visible: status === Image.Ready
        }

        Text {
            anchors.centerIn: parent
            text: root.fallback
            color: "#111217"
            font.pixelSize: Math.max(
                12,
                Math.round(parent.height * 0.34)
            )
            visible: icon.status !== Image.Ready
        }

        Rectangle {
            visible: root.active && root.badgeText !== ""
            width: Math.max(20, root.badgeText.length > 1 ? 28 : 20)
            height: width
            radius: width / 2
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.rightMargin: -4
            anchors.topMargin: -4
            color: root.activeBorderColor
            border.color: root.surfaceColor
            border.width: 2.5

            Text {
                anchors.centerIn: parent
                text: root.badgeText
                color: "#FFFFFF"
                font.pixelSize: root.badgeText.length > 1 ? 9 : 10
                font.weight: Font.Bold
            }
        }
    }

    MouseArea {
        id: mouseArea
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        acceptedButtons: Qt.LeftButton
        onClicked: root.clicked()
    }
}

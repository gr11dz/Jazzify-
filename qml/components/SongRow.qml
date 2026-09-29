import QtQuick
import QtQuick.Controls
import "../theme"

Item {
    id: root

    required property string title
    required property string artist
    required property string album
    required property string path
    required property string artworkPath
    required property string primaryColor
    required property string secondaryColor
    required property string backgroundColor

    property bool hovered: rowMouse.containsMouse

    signal playRequested(
        string path,
        string title,
        string artist,
        string album,
        string artwork,
        string primary,
        string secondary,
        string background
    )

    height: 68

    Rectangle {
        id: card
        anchors.fill: parent
        radius: 13
        color: root.hovered ? Colors.surface2 : Colors.surface
        border.width: root.hovered ? 1 : 0
        border.color: Qt.rgba(1, 1, 1, 0.06)

        Behavior on color { ColorAnimation { duration: 100 } }

        MouseArea {
            id: rowMouse
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor

            onClicked: root.playRequested(
                root.path,
                root.title,
                root.artist,
                root.album,
                root.artworkPath,
                root.primaryColor,
                root.secondaryColor,
                root.backgroundColor
            )
        }

        Rectangle {
            x: 10
            y: 10
            width: 48
            height: 48
            radius: 9
            color: Colors.surface3
            clip: true

            Image {
                anchors.fill: parent
                source: root.artworkPath
                    ? "file:///" + root.artworkPath.replace(/\\/g, "/")
                    : ""
                fillMode: Image.PreserveAspectCrop
                asynchronous: true
                cache: true
            }

            Text {
                anchors.centerIn: parent
                text: "♪"
                color: Colors.muted
                font.pixelSize: 20
                visible: parent.children.length === 0
            }
        }

        Column {
            x: 74
            y: 10
            width: root.width * 0.40
            spacing: 4

            Text {
                width: parent.width
                text: root.title || "Unknown title"
                color: Colors.text
                font.pixelSize: 14
                font.weight: Font.DemiBold
                elide: Text.ElideRight
            }

            Text {
                width: parent.width
                text: root.artist || "Unknown artist"
                color: Colors.muted
                font.pixelSize: 12
                elide: Text.ElideRight
            }
        }

        Text {
            x: root.width * 0.53
            width: root.width * 0.29
            anchors.verticalCenter: parent.verticalCenter
            text: root.album || "Unknown album"
            color: Colors.muted
            font.pixelSize: 13
            elide: Text.ElideRight
        }

        ControlIcon {
            id: playButton
            width: 42
            height: 42
            anchors.right: parent.right
            anchors.rightMargin: 12
            anchors.verticalCenter: parent.verticalCenter
            iconSource: "../../images/play.png"
            fallback: "▶"
            onClicked: root.playRequested(
                root.path,
                root.title,
                root.artist,
                root.album,
                root.artworkPath,
                root.primaryColor,
                root.secondaryColor,
                root.backgroundColor
            )
        }
    }
}

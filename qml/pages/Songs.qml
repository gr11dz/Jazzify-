import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import "../components"
import "../theme"

Item {
    id: page
    signal openSettingsRequested()

    FolderDialog {
        id: folderDialog
        title: "Choose a music folder"
        onAccepted: {
            let value = selectedFolder.toString()
            if (value.startsWith("file:///")) value = value.substring(8)
            library.addFolder(value)
        }
    }

    Column {
        anchors.fill: parent
        anchors.margins: 28
        spacing: 16

        Row {
            width: parent.width
            height: 54
            spacing: 12

            Column {
                width: parent.width - 184
                Text { text: "Songs"; color: Colors.text; font.pixelSize: 28; font.weight: Font.DemiBold }
                Text { text: library.songCount + " songs"; color: Colors.muted; font.pixelSize: 13 }
            }

            Button {
                text: "＋  Add folder"
                width: 132
                height: 42
                onClicked: folderDialog.open()
                background: Rectangle { radius: 12; color: Colors.accent }
                contentItem: Text { text: parent.text; color: "#0A0B10"; font.pixelSize: 13; font.weight: Font.DemiBold; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
            }

            ControlIcon {
                width: 42
                height: 42
                iconSource: "../../images/settings.png"
                fallback: "⚙"
                surfaceColor: Qt.rgba(0.92, 0.92, 0.94, 1)
                onClicked: page.openSettingsRequested()
            }
        }

        Row {
            width: parent.width
            height: 42
            spacing: 10

            Button {
                height: 38
                text: "Shuffle all"
                background: Rectangle { radius: 11; color: Colors.accentSoft }
                contentItem: Text { text: parent.text; color: Colors.accent; font.pixelSize: 13; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                onClicked: player.shuffleAll(library.playbackSongs())
            }

            Button {
                height: 38
                text: "Sort: Title"
                background: Rectangle { radius: 11; color: Colors.surface2 }
                contentItem: Text { text: parent.text; color: Colors.muted; font.pixelSize: 13; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
            }
        }

        Rectangle {
            width: parent.width
            height: 34
            radius: 10
            color: Colors.surface
            Text { x: 78; anchors.verticalCenter: parent.verticalCenter; text: "TITLE"; color: Colors.muted; font.pixelSize: 10 }
            Text { x: parent.width * 0.53; anchors.verticalCenter: parent.verticalCenter; text: "ALBUM"; color: Colors.muted; font.pixelSize: 10 }
        }

        ListView {
            id: songsList
            width: parent.width
            height: parent.height - 174
            clip: true
            spacing: 4
            model: library.songsModel

            delegate: SongRow {
                width: songsList.width - 4

                onPlayRequested: function(
                    songPath,
                    songTitle,
                    songArtist,
                    songAlbum,
                    songArtwork,
                    songPrimary,
                    songSecondary,
                    songBackground
                ) {
                    player.setQueue(library.playbackSongs())
                    player.playSong(
                        songPath,
                        songTitle,
                        songArtist,
                        songAlbum,
                        songArtwork,
                        songPrimary,
                        songSecondary,
                        songBackground
                    )
                }
            }

            ScrollBar.vertical: ScrollBar {}
        }
    }
}

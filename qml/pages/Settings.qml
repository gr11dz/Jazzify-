import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import "../theme"
import "../components"

Item {
    id: page
    signal backRequested()

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
        anchors.margins: 32
        spacing: 18

        Row {
            width: parent.width
            spacing: 12

            ControlIcon {
                width: 42
                height: 42
                iconSource: "../../images/back.png"
                fallback: "‹"
                onClicked: page.backRequested()
            }

            Column {
                Text { text: "Settings"; color: Colors.text; font.pixelSize: 28; font.weight: Font.DemiBold }
                Text { text: "Music Library"; color: Colors.muted; font.pixelSize: 13 }
            }
        }

        Rectangle {
            width: parent.width
            radius: 16
            color: Colors.surface
            height: 500

            Column {
                anchors.fill: parent
                anchors.margins: 20
                spacing: 12
                Text { text: "Music folders"; color: Colors.text; font.pixelSize: 16; font.weight: Font.DemiBold }
                Text { text: "Jazzify watches these folders for new, changed, and removed audio files."; color: Colors.muted; font.pixelSize: 12; wrapMode: Text.WordWrap; width: parent.width }
                Button {
                    text: "＋  Add music folder"
                    width: 180; height: 40
                    onClicked: folderDialog.open()
                    background: Rectangle { radius: 11; color: Colors.surface3 }
                    contentItem: Text { text: parent.text; color: Colors.text; font.pixelSize: 13; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                }
                Text {
                    text: "Indexed songs: " + library.songCount
                    color: Colors.muted
                    font.pixelSize: 12
                }

                Rectangle {
                    width: parent.width
                    height: 1
                    color: Qt.rgba(1, 1, 1, 0.06)
                }

                Row {
                    width: parent.width
                    height: 54
                    spacing: 14

                    Column {
                        width: parent.width - alwaysOnSwitch.width - 14
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: 3

                        Text {
                            text: "Keep waveform enabled"
                            color: Colors.text
                            font.pixelSize: 13
                            font.weight: Font.DemiBold
                        }

                        Text {
                            text: "Keep the audio visualizer active even when Jazzify is not focused."
                            color: Colors.muted
                            font.pixelSize: 11
                            wrapMode: Text.WordWrap
                            width: parent.width
                        }
                    }

                    Switch {
                        id: alwaysOnSwitch
                        anchors.verticalCenter: parent.verticalCenter
                        checked: settings.waveformAlwaysOn
                        onToggled: settings.setWaveformAlwaysOn(checked)
                    }
                }


            }
        }
    }
}

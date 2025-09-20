import Foundation
import AVFoundation
import os.log

class AudioPlayer: NSObject, ObservableObject {
    static let shared = AudioPlayer()
    
    private let logger = Logger(subsystem: "com.classicsviewer.app", category: "AudioPlayer")
    
    @Published var isPlaying = false
    @Published var currentLineNumber: Int? = nil
    
    private var player: AVAudioPlayer?
    private let audioDAO = AudioPackageDAO()
    
    private override init() {
        super.init()
        setupAudioSession()
    }
    
    private func setupAudioSession() {
        do {
            try AVAudioSession.sharedInstance().setCategory(.playback, mode: .default)
            try AVAudioSession.sharedInstance().setActive(true)
        } catch {
            logger.error("Failed to setup audio session: \(error)")
        }
    }
    
    func playAudioForLine(workId: String, bookId: String, lineNumber: Int) async {
        logger.info("Attempting to play audio for \(workId) book \(bookId) line \(lineNumber)")
        
        do {
            // Get audio files for this line
            let audioFiles = try await audioDAO.getAudioFiles(
                workId: workId,
                bookId: bookId,
                lineStart: lineNumber,
                lineEnd: lineNumber
            )
            
            guard let audioFile = audioFiles.first else {
                logger.info("No audio file found for line \(lineNumber)")
                return
            }
            
            // Get the full file path
            guard let filePath = try await audioDAO.getAudioFilePath(audioFileId: audioFile.id!) else {
                logger.error("Could not get file path for audio file \(audioFile.id ?? -1)")
                return
            }

            let fileURL = URL(fileURLWithPath: filePath)

            // Check if file exists
            guard FileManager.default.fileExists(atPath: filePath) else {
                logger.error("Audio file does not exist at path: \(filePath)")
                // Log additional debug info
                logger.error("Looking for: \(audioFile.filePath)")
                logger.error("Documents path: \(NSSearchPathForDirectoriesInDomains(.documentDirectory, .userDomainMask, true).first ?? "unknown")")
                return
            }
            
            logger.info("Playing audio file: \(fileURL.lastPathComponent)")
            
            await MainActor.run {
                do {
                    // Stop any current playback
                    player?.stop()
                    
                    // Create new player with the audio file
                    player = try AVAudioPlayer(contentsOf: fileURL)
                    player?.delegate = self
                    player?.prepareToPlay()
                    player?.play()
                    
                    isPlaying = true
                    currentLineNumber = lineNumber
                } catch {
                    logger.error("Failed to play audio: \(error)")
                }
            }
            
        } catch {
            logger.error("Failed to get audio files: \(error)")
        }
    }
    
    func stop() {
        player?.stop()
        isPlaying = false
        currentLineNumber = nil
    }
    
    func togglePlayPause() {
        if let player = player {
            if player.isPlaying {
                player.pause()
                isPlaying = false
            } else {
                player.play()
                isPlaying = true
            }
        }
    }
}

extension AudioPlayer: AVAudioPlayerDelegate {
    func audioPlayerDidFinishPlaying(_ player: AVAudioPlayer, successfully flag: Bool) {
        isPlaying = false
        currentLineNumber = nil
    }
    
    func audioPlayerDecodeErrorDidOccur(_ player: AVAudioPlayer, error: Error?) {
        logger.error("Audio decode error: \(error?.localizedDescription ?? "Unknown error")")
        isPlaying = false
        currentLineNumber = nil
    }
}
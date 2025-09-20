package com.classicsviewer.app.audio

import android.app.Service
import android.content.Intent
import android.net.Uri
import android.os.Binder
import android.os.IBinder
import android.util.Log
import com.google.android.exoplayer2.ExoPlayer
import com.google.android.exoplayer2.MediaItem
import com.google.android.exoplayer2.Player
import com.google.android.exoplayer2.source.ProgressiveMediaSource
import com.google.android.exoplayer2.upstream.DefaultDataSource
import java.io.File

class AudioPlaybackService : Service() {
    companion object {
        private const val TAG = "AudioPlaybackService"
        const val ACTION_PLAY = "com.classicsviewer.app.audio.ACTION_PLAY"
        const val ACTION_PAUSE = "com.classicsviewer.app.audio.ACTION_PAUSE"
        const val ACTION_STOP = "com.classicsviewer.app.audio.ACTION_STOP"
        const val EXTRA_AUDIO_FILE = "audio_file"
        const val EXTRA_CONTINUOUS = "continuous_mode"
    }
    
    private val binder = LocalBinder()
    private var exoPlayer: ExoPlayer? = null
    private var currentFile: File? = null
    private var continuousMode = false
    private var playbackListener: PlaybackListener? = null
    
    interface PlaybackListener {
        fun onPlaybackStarted(file: File)
        fun onPlaybackCompleted()
        fun onPlaybackError(error: String)
        fun onPlaybackProgress(currentPosition: Long, duration: Long)
    }
    
    inner class LocalBinder : Binder() {
        fun getService(): AudioPlaybackService = this@AudioPlaybackService
    }
    
    override fun onCreate() {
        super.onCreate()
        initializePlayer()
    }
    
    override fun onBind(intent: Intent?): IBinder = binder
    
    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            ACTION_PLAY -> {
                val filePath = intent.getStringExtra(EXTRA_AUDIO_FILE)
                continuousMode = intent.getBooleanExtra(EXTRA_CONTINUOUS, false)
                filePath?.let { playAudio(File(it)) }
            }
            ACTION_PAUSE -> pausePlayback()
            ACTION_STOP -> stopPlayback()
        }
        return START_NOT_STICKY
    }
    
    private fun initializePlayer() {
        if (exoPlayer == null) {
            exoPlayer = ExoPlayer.Builder(this).build().apply {
                addListener(object : Player.Listener {
                    override fun onPlaybackStateChanged(playbackState: Int) {
                        when (playbackState) {
                            Player.STATE_ENDED -> {
                                Log.d(TAG, "Playback completed")
                                playbackListener?.onPlaybackCompleted()
                                if (!continuousMode) {
                                    stopSelf()
                                }
                            }
                            Player.STATE_READY -> {
                                Log.d(TAG, "Player ready")
                                currentFile?.let {
                                    playbackListener?.onPlaybackStarted(it)
                                }
                            }
                            Player.STATE_BUFFERING -> {
                                Log.d(TAG, "Buffering...")
                            }
                            Player.STATE_IDLE -> {
                                Log.d(TAG, "Player idle")
                            }
                        }
                    }
                    
                    override fun onPlayerError(error: com.google.android.exoplayer2.PlaybackException) {
                        Log.e(TAG, "Playback error: ${error.message}")
                        playbackListener?.onPlaybackError(error.message ?: "Unknown error")
                    }
                })
            }
        }
    }
    
    fun playAudio(file: File) {
        if (!file.exists()) {
            Log.e(TAG, "Audio file does not exist: ${file.absolutePath}")
            playbackListener?.onPlaybackError("Audio file not found")
            return
        }
        
        try {
            // Check file extension for supported formats
            val extension = file.extension.lowercase()
            val supportedFormats = listOf("mp3", "mp4", "m4a", "wav", "ogg", "aac", "flac")
            
            if (extension == "mid" || extension == "midi") {
                Log.w(TAG, "MIDI format may not be supported on this device: ${file.name}")
                // Still try to play it, but warn the user
            } else if (extension !in supportedFormats) {
                Log.w(TAG, "Unknown audio format: $extension")
            }
            
            currentFile = file
            val uri = Uri.fromFile(file)
            val mediaItem = MediaItem.fromUri(uri)
            
            exoPlayer?.apply {
                stop()
                clearMediaItems()
                setMediaItem(mediaItem)
                prepare()
                play()
            }
            
            Log.d(TAG, "Playing audio: ${file.name}")
        } catch (e: Exception) {
            Log.e(TAG, "Error playing audio: ${e.message}", e)
            // Don't crash - just notify the listener
            playbackListener?.onPlaybackError("Unable to play this audio format")
            currentFile = null
        }
    }
    
    fun pausePlayback() {
        exoPlayer?.pause()
        Log.d(TAG, "Playback paused")
    }
    
    fun resumePlayback() {
        exoPlayer?.play()
        Log.d(TAG, "Playback resumed")
    }
    
    fun stopPlayback() {
        exoPlayer?.stop()
        exoPlayer?.clearMediaItems()
        currentFile = null
        Log.d(TAG, "Playback stopped")
    }
    
    fun isPlaying(): Boolean = exoPlayer?.isPlaying ?: false
    
    fun setPlaybackListener(listener: PlaybackListener?) {
        playbackListener = listener
    }
    
    fun getCurrentPosition(): Long = exoPlayer?.currentPosition ?: 0
    
    fun getDuration(): Long = exoPlayer?.duration ?: 0
    
    fun seekTo(position: Long) {
        exoPlayer?.seekTo(position)
    }
    
    fun setContinuousMode(enabled: Boolean) {
        continuousMode = enabled
    }
    
    override fun onDestroy() {
        super.onDestroy()
        exoPlayer?.release()
        exoPlayer = null
        playbackListener = null
        Log.d(TAG, "Service destroyed")
    }
}
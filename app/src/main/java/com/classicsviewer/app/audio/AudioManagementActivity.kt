package com.classicsviewer.app.audio

import android.app.Activity
import android.net.Uri
import android.os.Bundle
import android.util.Log
import android.view.MenuItem
import android.view.View
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AlertDialog
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.work.WorkInfo
import androidx.work.WorkManager
import com.classicsviewer.app.BaseActivity
import com.classicsviewer.app.R
import com.classicsviewer.app.databinding.ActivityAudioManagementBinding
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.text.SimpleDateFormat
import java.util.*

class AudioManagementActivity : BaseActivity() {
    companion object {
        private const val TAG = "AudioManagement"
    }
    
    private lateinit var binding: ActivityAudioManagementBinding
    private lateinit var audioRepository: AudioRepository
    private lateinit var adapter: AudioPackageAdapter
    private var packages = mutableListOf<AudioPackage>()
    private lateinit var workManager: WorkManager
    private var currentWorkId: UUID? = null
    
    private val pickZipLauncher = registerForActivityResult(
        ActivityResultContracts.GetContent()
    ) { uri: Uri? ->
        uri?.let { importAudioPackage(it) }
    }
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityAudioManagementBinding.inflate(layoutInflater)
        setContentView(binding.root)
        
        supportActionBar?.apply {
            setDisplayHomeAsUpEnabled(true)
            title = "Manage Audio Packages"
        }
        
        audioRepository = AudioRepository(this)
        workManager = WorkManager.getInstance(this)
        setupRecyclerView()
        setupButtons()
        loadPackages()
    }
    
    private fun setupRecyclerView() {
        adapter = AudioPackageAdapter(
            packages,
            onPackageSelected = { packageId ->
                setActivePackage(packageId)
            },
            onPackageDeleted = { packageId ->
                confirmDeletePackage(packageId)
            }
        )
        
        binding.recyclerPackages.apply {
            layoutManager = LinearLayoutManager(this@AudioManagementActivity)
            adapter = this@AudioManagementActivity.adapter
        }
    }
    
    private fun setupButtons() {
        binding.fabImportAudio.setOnClickListener {
            pickZipLauncher.launch("application/zip")
        }
    }
    
    private fun loadPackages() {
        lifecycleScope.launch {
            try {
                val loadedPackages = audioRepository.getAllPackages()
                Log.d(TAG, "Loaded ${loadedPackages.size} packages")
                loadedPackages.forEach { pkg ->
                    Log.d(TAG, "Package: ${pkg.packageName}, isActive=${pkg.isActive}")
                }
                packages.clear()
                packages.addAll(loadedPackages)
                adapter.notifyDataSetChanged()
                
                updateEmptyState()
            } catch (e: Exception) {
                Log.e(TAG, "Error loading packages", e)
                Toast.makeText(this@AudioManagementActivity, 
                    "Failed to load audio packages", Toast.LENGTH_SHORT).show()
            }
        }
    }
    
    private fun updateEmptyState() {
        if (packages.isEmpty()) {
            binding.emptyStateLayout.visibility = View.VISIBLE
            binding.recyclerPackages.visibility = View.GONE
        } else {
            binding.emptyStateLayout.visibility = View.GONE
            binding.recyclerPackages.visibility = View.VISIBLE
        }
    }
    
    private fun setActivePackage(packageId: Long) {
        lifecycleScope.launch {
            try {
                binding.progressBar.visibility = View.VISIBLE
                
                val success = audioRepository.setActivePackage(packageId)
                if (success) {
                    // Update UI to reflect new active package
                    packages.forEach { pkg ->
                        pkg.isActive = pkg.id == packageId
                    }
                    adapter.notifyDataSetChanged()
                    Toast.makeText(this@AudioManagementActivity, 
                        "Audio package activated", Toast.LENGTH_SHORT).show()
                } else {
                    Toast.makeText(this@AudioManagementActivity, 
                        "Failed to activate package", Toast.LENGTH_SHORT).show()
                }
            } catch (e: Exception) {
                Log.e(TAG, "Error setting active package", e)
                Toast.makeText(this@AudioManagementActivity, 
                    "Error: ${e.message}", Toast.LENGTH_SHORT).show()
            } finally {
                binding.progressBar.visibility = View.GONE
            }
        }
    }
    
    private fun confirmDeletePackage(packageId: Long) {
        val packageToDelete = packages.find { it.id == packageId }
        packageToDelete?.let { pkg ->
            val dialog = com.google.android.material.dialog.MaterialAlertDialogBuilder(this)
                .setTitle("Delete Audio Package")
                .setMessage("Delete '${pkg.packageName}'? This will remove all audio files for this package.")
                .setPositiveButton("Delete") { _, _ ->
                    deletePackage(packageId)
                }
                .setNegativeButton("Cancel", null)
                .show()

            // Make buttons visible on all devices
            dialog.getButton(android.app.AlertDialog.BUTTON_POSITIVE)?.setTextColor(
                resources.getColor(android.R.color.holo_blue_light, null)
            )
            dialog.getButton(android.app.AlertDialog.BUTTON_NEGATIVE)?.setTextColor(
                resources.getColor(android.R.color.holo_blue_light, null)
            )
        }
    }
    
    private fun deletePackage(packageId: Long) {
        lifecycleScope.launch {
            try {
                binding.progressBar.visibility = View.VISIBLE
                
                val success = audioRepository.deletePackage(packageId)
                if (success) {
                    packages.removeAll { it.id == packageId }
                    adapter.notifyDataSetChanged()
                    updateEmptyState()
                    Toast.makeText(this@AudioManagementActivity, 
                        "Package deleted", Toast.LENGTH_SHORT).show()
                } else {
                    Toast.makeText(this@AudioManagementActivity, 
                        "Failed to delete package", Toast.LENGTH_SHORT).show()
                }
            } catch (e: Exception) {
                Log.e(TAG, "Error deleting package", e)
                Toast.makeText(this@AudioManagementActivity, 
                    "Error: ${e.message}", Toast.LENGTH_SHORT).show()
            } finally {
                binding.progressBar.visibility = View.GONE
            }
        }
    }
    
    private fun importAudioPackage(uri: Uri) {
        lifecycleScope.launch {
            try {
                // Show import progress UI immediately
                binding.importProgressCard.visibility = View.VISIBLE
                binding.importProgressText.text = "Starting import..."
                binding.importProgressBar.isIndeterminate = true
                binding.importProgressDetails.text = "Processing file..."
                
                // Create and enqueue work request
                val workRequest = AudioImportWorker.createWorkRequest(uri)
                currentWorkId = workRequest.id
                
                workManager.enqueue(workRequest)
                
                // Observe work progress
                workManager.getWorkInfoByIdLiveData(workRequest.id).observe(this@AudioManagementActivity) { workInfo ->
                    if (workInfo != null) {
                        when (workInfo.state) {
                            WorkInfo.State.RUNNING -> {
                                val status = workInfo.progress.getString(AudioImportWorker.KEY_STATUS) ?: "Processing..."
                                val details = workInfo.progress.getString(AudioImportWorker.KEY_DETAILS) ?: ""
                                val book = workInfo.progress.getInt(AudioImportWorker.KEY_BOOK, 0)
                                updateImportProgress(status, -1, details, book)
                            }
                            WorkInfo.State.SUCCEEDED -> {
                                val filesImported = workInfo.outputData.getInt(AudioImportWorker.KEY_FILES_IMPORTED, 0)
                                updateImportProgress("Import complete", 100, "$filesImported files imported successfully", 0)
                            }
                            WorkInfo.State.FAILED -> {
                                val error = workInfo.outputData.getString(AudioImportWorker.KEY_ERROR) ?: "Unknown error"
                                updateImportProgress("Import failed", -1, error, 0)
                                Toast.makeText(this@AudioManagementActivity, error, Toast.LENGTH_LONG).show()
                            }
                            WorkInfo.State.CANCELLED -> {
                                binding.importProgressCard.visibility = View.GONE
                            }
                            else -> { /* ENQUEUED, BLOCKED states - no action needed */ }
                        }
                    }
                }
                    
            } catch (e: Exception) {
                Log.e(TAG, "Error starting import", e)
                Toast.makeText(this@AudioManagementActivity, 
                    "Failed to import audio: ${e.message}", Toast.LENGTH_SHORT).show()
                binding.importProgressCard.visibility = View.GONE
            }
        }
    }
    
    private fun updateImportProgress(status: String, progress: Int, details: String, book: Int) {
        runOnUiThread {
            try {
                binding.importProgressCard.visibility = View.VISIBLE
                binding.importProgressText.text = status
                
                if (progress >= 0) {
                    binding.importProgressBar.isIndeterminate = false
                    binding.importProgressBar.progress = progress
                } else {
                    binding.importProgressBar.isIndeterminate = true
                }
                
                binding.importProgressDetails.text = details
                
                // Hide progress after completion
                if (status.contains("complete", ignoreCase = true)) {
                    binding.importProgressCard.postDelayed({
                        binding.importProgressCard.visibility = View.GONE
                        loadPackages() // Refresh the list
                    }, 2000)
                }
            } catch (e: Exception) {
                Log.e(TAG, "Error updating import progress", e)
            }
        }
    }
    
    override fun onOptionsItemSelected(item: MenuItem): Boolean {
        return when (item.itemId) {
            android.R.id.home -> {
                onBackPressedDispatcher.onBackPressed()
                true
            }
            else -> super.onOptionsItemSelected(item)
        }
    }
    
    override fun onResume() {
        super.onResume()
        loadPackages()
    }
    
    override fun onDestroy() {
        super.onDestroy()
        // Cancel work if activity is destroyed
        currentWorkId?.let {
            workManager.cancelWorkById(it)
        }
    }
}
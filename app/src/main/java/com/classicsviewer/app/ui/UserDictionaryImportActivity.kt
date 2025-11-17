package com.classicsviewer.app.ui

import android.net.Uri
import android.os.Bundle
import android.view.MenuItem
import android.view.View
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AlertDialog
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.lifecycleScope
import com.classicsviewer.app.BaseActivity
import com.classicsviewer.app.databinding.ActivityUserDictionaryImportBinding
import com.classicsviewer.app.repository.UserDictionaryRepository
import com.classicsviewer.app.viewmodels.UserDictionaryViewModel
import kotlinx.coroutines.launch

class UserDictionaryImportActivity : BaseActivity() {
    
    private lateinit var binding: ActivityUserDictionaryImportBinding
    private lateinit var viewModel: UserDictionaryViewModel
    
    private val pickZipLauncher = registerForActivityResult(
        ActivityResultContracts.GetContent()
    ) { uri: Uri? ->
        uri?.let { importDictionary(it) }
    }
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityUserDictionaryImportBinding.inflate(layoutInflater)
        setContentView(binding.root)
        
        supportActionBar?.apply {
            setDisplayHomeAsUpEnabled(true)
            title = "Manage Dictionary"
        }
        
        viewModel = ViewModelProvider(this)[UserDictionaryViewModel::class.java]
        
        setupObservers()
        setupButtons()
    }
    
    private fun setupObservers() {
        viewModel.dictionaryInfo.observe(this) { info ->
            updateUI(info)
        }
        
        viewModel.isLoading.observe(this) { isLoading ->
            binding.progressBar.visibility = if (isLoading) View.VISIBLE else View.GONE
            binding.selectDictionaryButton.isEnabled = !isLoading
            binding.removeDictionaryButton.isEnabled = !isLoading
        }
        
        viewModel.importState.observe(this) { state ->
            when (state) {
                is UserDictionaryViewModel.ImportState.Importing -> {
                    binding.progressBar.visibility = View.VISIBLE
                    binding.progressBar.isIndeterminate = false
                    binding.progressBar.progress = state.progress
                    binding.statusText.text = state.message
                }
                is UserDictionaryViewModel.ImportState.Success -> {
                    binding.progressBar.visibility = View.GONE
                    Toast.makeText(
                        this,
                        "Dictionary imported successfully\n${state.lemmaCount} entries, ${state.mappingCount} mappings\nRestarting...",
                        Toast.LENGTH_SHORT
                    ).show()

                    viewModel.resetImportState()

                    // Restart app immediately to clear all caches and load new dictionary
                    restartApp()
                }
                is UserDictionaryViewModel.ImportState.Error -> {
                    binding.progressBar.visibility = View.GONE
                    Toast.makeText(
                        this,
                        "Import failed: ${state.message}",
                        Toast.LENGTH_LONG
                    ).show()
                    viewModel.resetImportState()
                }
                else -> {
                    // Idle state - no action needed
                }
            }
        }
    }
    
    private fun setupButtons() {
        binding.selectDictionaryButton.setOnClickListener {
            pickZipLauncher.launch("application/zip")
        }
        
        binding.switchDictionaryButton.setOnClickListener {
            showDictionarySwitcher()
        }
        
        binding.removeDictionaryButton.setOnClickListener {
            confirmRemoveDictionary()
        }
    }
    
    private fun updateUI(info: UserDictionaryRepository.DictionaryInfo?) {
        if (info != null) {
            // Dictionary is loaded
            binding.statusText.text = "Current dictionary: ${info.fileName}"
            binding.dictionaryInfoText.visibility = View.VISIBLE
            binding.dictionaryInfoText.text = buildString {
                appendLine("Greek: ${info.greekLemmaCount} entries, ${info.greekMappingCount} morphology mappings")
                append("Latin: ${info.latinLemmaCount} entries, ${info.latinMappingCount} morphology mappings")
            }
            binding.selectDictionaryButton.text = "Import New Dictionary"
            binding.switchDictionaryButton.visibility = View.VISIBLE
            binding.removeDictionaryButton.visibility = View.VISIBLE
        } else {
            // No dictionary loaded
            binding.statusText.text = "No custom dictionary selected"
            binding.dictionaryInfoText.visibility = View.GONE
            binding.selectDictionaryButton.text = "Select Dictionary ZIP"
            binding.switchDictionaryButton.visibility = View.GONE
            binding.removeDictionaryButton.visibility = View.GONE
        }
    }
    
    private fun importDictionary(uri: Uri) {
        viewModel.importDictionary(uri)
    }
    
    private fun confirmRemoveDictionary() {
        val dialog = com.google.android.material.dialog.MaterialAlertDialogBuilder(this)
            .setTitle("Remove Dictionary")
            .setMessage("Remove the custom dictionary? This will delete all imported entries and morphology mappings.")
            .setPositiveButton("Remove") { _, _ ->
                removeDictionary()
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
    
    private fun removeDictionary() {
        lifecycleScope.launch(kotlinx.coroutines.Dispatchers.IO) {
            try {
                viewModel.clearDictionary()

                kotlinx.coroutines.withContext(kotlinx.coroutines.Dispatchers.Main) {
                    Toast.makeText(this@UserDictionaryImportActivity,
                        "Dictionary removed - restarting...",
                        Toast.LENGTH_SHORT).show()

                    // Use the same restart method
                    restartApp()
                }
            } catch (e: Exception) {
                kotlinx.coroutines.withContext(kotlinx.coroutines.Dispatchers.Main) {
                    Toast.makeText(this@UserDictionaryImportActivity,
                        "Error: ${e.message}",
                        Toast.LENGTH_SHORT).show()
                }
            }
        }
    }

    private fun restartApp() {
        try {
            android.util.Log.d("UserDictionaryImport", "Starting app restart...")

            // Force app restart - identical to MainActivity database import
            val intent = packageManager.getLaunchIntentForPackage(packageName)
            if (intent == null) {
                android.util.Log.e("UserDictionaryImport", "Failed to get launch intent for package: $packageName")
                return
            }

            intent.addFlags(android.content.Intent.FLAG_ACTIVITY_CLEAR_TOP or android.content.Intent.FLAG_ACTIVITY_NEW_TASK or android.content.Intent.FLAG_ACTIVITY_CLEAR_TASK)

            android.util.Log.d("UserDictionaryImport", "Starting activity with intent")
            startActivity(intent)

            // Exclude from recents and finish
            if (android.os.Build.VERSION.SDK_INT >= 21) {
                android.util.Log.d("UserDictionaryImport", "Calling finishAndRemoveTask()")
                finishAndRemoveTask()
            } else {
                android.util.Log.d("UserDictionaryImport", "Calling finish()")
                finish()
            }

            // Delay to ensure cleanup, then exit
            android.util.Log.d("UserDictionaryImport", "Scheduling System.exit(0) in 100ms")
            android.os.Handler(android.os.Looper.getMainLooper()).postDelayed({
                android.util.Log.d("UserDictionaryImport", "Executing System.exit(0)")
                System.exit(0)
            }, 100)
        } catch (e: Exception) {
            android.util.Log.e("UserDictionaryImport", "Exception during restart", e)
            Toast.makeText(this, "Restart failed: ${e.message}", Toast.LENGTH_LONG).show()
        }
    }
    
    private fun showWarningsDialog(warnings: List<String>) {
        val message = warnings.take(10).joinToString("\n") + 
            if (warnings.size > 10) "\n... and ${warnings.size - 10} more" else ""
            
        com.google.android.material.dialog.MaterialAlertDialogBuilder(this)
            .setTitle("Import Warnings")
            .setMessage(message)
            .setPositiveButton("OK", null)
            .show()
    }
    
    private fun showDictionarySwitcher() {
        lifecycleScope.launch {
            val packages = viewModel.getAllPackages()
            val activePackage = viewModel.getActivePackage()
            
            if (packages.isEmpty()) {
                Toast.makeText(this@UserDictionaryImportActivity, "No dictionaries available", Toast.LENGTH_SHORT).show()
                return@launch
            }
            
            val packageNames = packages.map { pkg ->
                val isActive = pkg.id == activePackage?.id
                val label = "${pkg.packageName} (${pkg.greekLemmas} Greek, ${pkg.latinLemmas} Latin)"
                if (isActive) "✓ $label" else label
            }.toTypedArray()
            
            com.google.android.material.dialog.MaterialAlertDialogBuilder(this@UserDictionaryImportActivity)
                .setTitle("Select Dictionary")
                .setSingleChoiceItems(packageNames, packages.indexOfFirst { it.id == activePackage?.id }) { dialog, which ->
                    val selectedPackage = packages[which]
                    lifecycleScope.launch {
                        viewModel.setActivePackage(selectedPackage.id)
                        Toast.makeText(
                            this@UserDictionaryImportActivity,
                            "Switched to: ${selectedPackage.packageName} - restarting...",
                            Toast.LENGTH_SHORT
                        ).show()
                        dialog.dismiss()

                        // Restart app to clear all caches
                        restartApp()
                    }
                }
                .setNegativeButton("Cancel", null)
                .show()
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
}
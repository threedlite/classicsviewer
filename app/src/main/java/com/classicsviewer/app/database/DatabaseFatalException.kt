package com.classicsviewer.app.database

/**
 * Custom exception thrown when database cannot be initialized.
 * Activities should catch this and handle gracefully.
 */
class DatabaseFatalException(message: String = "Database initialization failed") : Exception(message)
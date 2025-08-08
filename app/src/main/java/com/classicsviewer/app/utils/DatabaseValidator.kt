package com.classicsviewer.app.utils

import android.content.Context
import android.database.sqlite.SQLiteDatabase
import android.net.Uri
import java.io.File

object DatabaseValidator {
    
    data class ValidationResult(
        val isValid: Boolean,
        val errorMessage: String? = null,
        val missingTables: List<String> = emptyList(),
        val schemaMismatches: List<String> = emptyList()
    )
    
    data class TableSchema(
        val name: String,
        val columns: Map<String, ColumnInfo>
    )
    
    data class ColumnInfo(
        val type: String,
        val notNull: Boolean,
        val defaultValue: String?,
        val primaryKey: Boolean
    )
    
    fun validateDatabase(context: Context, uri: Uri): ValidationResult {
        val tempFile = File(context.cacheDir, "temp_validation.db")
        
        try {
            // Copy the database to a temporary file for validation
            context.contentResolver.openInputStream(uri)?.use { input ->
                tempFile.outputStream().use { output ->
                    input.copyTo(output)
                }
            } ?: return ValidationResult(false, "Could not open database file")
            
            // Get the bundled database schema for comparison
            val bundledDbPath = context.getDatabasePath("perseus_texts.db").absolutePath
            if (!File(bundledDbPath).exists()) {
                return ValidationResult(false, "Bundled database not found. Please launch the app normally first.")
            }
            
            // Open both databases for comparison
            val externalDb = SQLiteDatabase.openDatabase(
                tempFile.absolutePath,
                null,
                SQLiteDatabase.OPEN_READONLY
            )
            
            val bundledDb = SQLiteDatabase.openDatabase(
                bundledDbPath,
                null,
                SQLiteDatabase.OPEN_READONLY
            )
            
            return externalDb.use { extDb ->
                bundledDb.use { bunDb ->
                    compareSchemas(extDb, bunDb)
                }
            }
            
        } catch (e: Exception) {
            return ValidationResult(false, "Invalid SQLite database: ${e.message}")
        } finally {
            tempFile.delete()
        }
    }
    
    private fun compareSchemas(externalDb: SQLiteDatabase, bundledDb: SQLiteDatabase): ValidationResult {
        val missingTables = mutableListOf<String>()
        val schemaMismatches = mutableListOf<String>()
        
        // Get all tables from bundled database
        val bundledTables = getTables(bundledDb)
        val externalTables = getTables(externalDb)
        
        // Check each bundled table exists in external database
        for (tableName in bundledTables) {
            if (tableName !in externalTables) {
                missingTables.add(tableName)
            } else {
                // Compare table schemas
                val bundledSchema = getTableSchema(bundledDb, tableName)
                val externalSchema = getTableSchema(externalDb, tableName)
                
                val schemaErrors = compareTableSchemas(tableName, bundledSchema, externalSchema)
                schemaMismatches.addAll(schemaErrors)
            }
        }
        
        return when {
            missingTables.isNotEmpty() -> {
                ValidationResult(
                    false,
                    "Missing required tables: ${missingTables.joinToString(", ")}",
                    missingTables
                )
            }
            schemaMismatches.isNotEmpty() -> {
                ValidationResult(
                    false,
                    "Schema mismatches found:\n${schemaMismatches.joinToString("\n")}",
                    schemaMismatches = schemaMismatches
                )
            }
            else -> {
                ValidationResult(true, "Database validation successful")
            }
        }
    }
    
    private fun getTables(db: SQLiteDatabase): List<String> {
        val tables = mutableListOf<String>()
        val cursor = db.rawQuery(
            "SELECT name FROM sqlite_master WHERE type='table' " +
            "AND name NOT LIKE 'android_%' " +
            "AND name != 'sqlite_sequence' " +
            "AND name != 'room_master_table'",  // Exclude Room's metadata table
            null
        )
        cursor.use {
            while (it.moveToNext()) {
                tables.add(it.getString(0))
            }
        }
        return tables
    }
    
    private fun getTableSchema(db: SQLiteDatabase, tableName: String): TableSchema {
        val columns = mutableMapOf<String, ColumnInfo>()
        val cursor = db.rawQuery("PRAGMA table_info($tableName)", null)
        
        cursor.use {
            while (it.moveToNext()) {
                val name = it.getString(it.getColumnIndex("name"))
                val type = it.getString(it.getColumnIndex("type"))
                val notNull = it.getInt(it.getColumnIndex("notnull")) == 1
                val defaultValue = it.getString(it.getColumnIndex("dflt_value"))
                val primaryKey = it.getInt(it.getColumnIndex("pk")) > 0
                
                columns[name] = ColumnInfo(type, notNull, defaultValue, primaryKey)
            }
        }
        
        return TableSchema(tableName, columns)
    }
    
    private fun compareTableSchemas(
        tableName: String,
        bundledSchema: TableSchema,
        externalSchema: TableSchema
    ): List<String> {
        val errors = mutableListOf<String>()
        
        // Check all bundled columns exist in external table
        for ((columnName, bundledColumn) in bundledSchema.columns) {
            val externalColumn = externalSchema.columns[columnName]
            
            when {
                externalColumn == null -> {
                    errors.add("Table '$tableName' missing column '$columnName'")
                }
                !isTypeCompatible(externalColumn.type, bundledColumn.type) -> {
                    errors.add("Table '$tableName' column '$columnName' has type '${externalColumn.type}', expected '${bundledColumn.type}'")
                }
                externalColumn.notNull != bundledColumn.notNull -> {
                    errors.add("Table '$tableName' column '$columnName' nullability mismatch")
                }
                externalColumn.primaryKey != bundledColumn.primaryKey -> {
                    errors.add("Table '$tableName' column '$columnName' primary key mismatch")
                }
            }
        }
        
        return errors
    }
    
    private fun isTypeCompatible(actualType: String, expectedType: String): Boolean {
        // SQLite is flexible with types, so we'll be lenient
        val actual = actualType.uppercase()
        val expected = expectedType.uppercase()
        
        return when {
            actual == expected -> true
            actual.contains(expected) -> true
            expected.contains(actual) -> true
            // INTEGER and INT are compatible
            (actual == "INT" && expected == "INTEGER") -> true
            (actual == "INTEGER" && expected == "INT") -> true
            // TEXT, VARCHAR, CHAR are all compatible
            (listOf("TEXT", "VARCHAR", "CHAR").any { actual.contains(it) } && 
             listOf("TEXT", "VARCHAR", "CHAR").any { expected.contains(it) }) -> true
            // REAL, FLOAT, DOUBLE are compatible
            (listOf("REAL", "FLOAT", "DOUBLE").any { actual.contains(it) } &&
             listOf("REAL", "FLOAT", "DOUBLE").any { expected.contains(it) }) -> true
            else -> false
        }
    }
}
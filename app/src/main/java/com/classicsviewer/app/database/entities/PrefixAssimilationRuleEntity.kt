package com.classicsviewer.app.database.entities

import androidx.room.ColumnInfo
import androidx.room.Entity
import androidx.room.Index
import androidx.room.PrimaryKey

/**
 * Entity for prefix assimilation rules used in compound word decomposition.
 *
 * This entity defines the structure but is NOT added to any @Database entities list.
 * The table is created dynamically during database build and accessed via raw SQL queries.
 *
 * Example: Greek κατορθόω → κατα (base_prefix) + κατ (assimilated_form) + ορθόω (stem)
 * Example: Latin compono → con (base_prefix) + com (assimilated_form) + pono (stem)
 */
@Entity(
    tableName = "prefix_assimilation_rules",
    indices = [
        Index(value = ["language"]),
        Index(value = ["base_prefix"]),
        Index(value = ["assimilated_form"]),
        Index(value = ["language", "priority"])
    ]
)
data class PrefixAssimilationRuleEntity(
    @PrimaryKey(autoGenerate = true)
    val id: Long = 0,

    @ColumnInfo(name = "language")
    val language: String,

    @ColumnInfo(name = "base_prefix")
    val basePrefix: String,

    @ColumnInfo(name = "assimilated_form")
    val assimilatedForm: String,

    @ColumnInfo(name = "meaning")
    val meaning: String?,

    @ColumnInfo(name = "phonological_rule")
    val phonologicalRule: String?,

    @ColumnInfo(name = "priority")
    val priority: Int,

    @ColumnInfo(name = "examples")
    val examples: String?
)

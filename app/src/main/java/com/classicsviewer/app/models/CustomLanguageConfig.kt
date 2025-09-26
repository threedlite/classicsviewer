package com.classicsviewer.app.models

import com.google.gson.annotations.SerializedName

data class CustomLanguageConfig(
    @SerializedName("id")
    val id: String,
    @SerializedName("displayName")
    val displayName: String,
    @SerializedName("color")
    val color: Int
)
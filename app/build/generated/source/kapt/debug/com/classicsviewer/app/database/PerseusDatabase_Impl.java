package com.classicsviewer.app.database;

import androidx.annotation.NonNull;
import androidx.room.DatabaseConfiguration;
import androidx.room.InvalidationTracker;
import androidx.room.RoomDatabase;
import androidx.room.RoomOpenHelper;
import androidx.room.migration.AutoMigrationSpec;
import androidx.room.migration.Migration;
import androidx.room.util.DBUtil;
import androidx.room.util.TableInfo;
import androidx.sqlite.db.SupportSQLiteDatabase;
import androidx.sqlite.db.SupportSQLiteOpenHelper;
import com.classicsviewer.app.database.dao.AuthorDao;
import com.classicsviewer.app.database.dao.AuthorDao_Impl;
import com.classicsviewer.app.database.dao.BookDao;
import com.classicsviewer.app.database.dao.BookDao_Impl;
import com.classicsviewer.app.database.dao.DictionaryDao;
import com.classicsviewer.app.database.dao.DictionaryDao_Impl;
import com.classicsviewer.app.database.dao.LemmaDao;
import com.classicsviewer.app.database.dao.LemmaDao_Impl;
import com.classicsviewer.app.database.dao.LemmaMapDao;
import com.classicsviewer.app.database.dao.LemmaMapDao_Impl;
import com.classicsviewer.app.database.dao.TextLineDao;
import com.classicsviewer.app.database.dao.TextLineDao_Impl;
import com.classicsviewer.app.database.dao.TranslationSegmentDao;
import com.classicsviewer.app.database.dao.TranslationSegmentDao_Impl;
import com.classicsviewer.app.database.dao.WordFormDao;
import com.classicsviewer.app.database.dao.WordFormDao_Impl;
import com.classicsviewer.app.database.dao.WorkDao;
import com.classicsviewer.app.database.dao.WorkDao_Impl;
import java.lang.Class;
import java.lang.Override;
import java.lang.String;
import java.lang.SuppressWarnings;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import javax.annotation.processing.Generated;

@Generated("androidx.room.RoomProcessor")
@SuppressWarnings({"unchecked", "deprecation"})
public final class PerseusDatabase_Impl extends PerseusDatabase {
  private volatile AuthorDao _authorDao;

  private volatile WorkDao _workDao;

  private volatile BookDao _bookDao;

  private volatile TextLineDao _textLineDao;

  private volatile WordFormDao _wordFormDao;

  private volatile LemmaDao _lemmaDao;

  private volatile LemmaMapDao _lemmaMapDao;

  private volatile DictionaryDao _dictionaryDao;

  private volatile TranslationSegmentDao _translationSegmentDao;

  @Override
  @NonNull
  protected SupportSQLiteOpenHelper createOpenHelper(@NonNull final DatabaseConfiguration config) {
    final SupportSQLiteOpenHelper.Callback _openCallback = new RoomOpenHelper(config, new RoomOpenHelper.Delegate(2) {
      @Override
      public void createAllTables(@NonNull final SupportSQLiteDatabase db) {
        db.execSQL("CREATE TABLE IF NOT EXISTS `authors` (`id` TEXT NOT NULL, `name` TEXT NOT NULL, `name_alt` TEXT, `language` TEXT NOT NULL, PRIMARY KEY(`id`))");
        db.execSQL("CREATE INDEX IF NOT EXISTS `idx_authors_language` ON `authors` (`language`)");
        db.execSQL("CREATE TABLE IF NOT EXISTS `works` (`id` TEXT NOT NULL, `author_id` TEXT NOT NULL, `title` TEXT NOT NULL, `title_alt` TEXT, `title_english` TEXT, `type` TEXT, `urn` TEXT, `description` TEXT, PRIMARY KEY(`id`), FOREIGN KEY(`author_id`) REFERENCES `authors`(`id`) ON UPDATE NO ACTION ON DELETE CASCADE )");
        db.execSQL("CREATE INDEX IF NOT EXISTS `idx_works_author` ON `works` (`author_id`)");
        db.execSQL("CREATE TABLE IF NOT EXISTS `books` (`id` TEXT NOT NULL, `work_id` TEXT NOT NULL, `book_number` INTEGER NOT NULL, `label` TEXT, `start_line` INTEGER, `end_line` INTEGER, `line_count` INTEGER, PRIMARY KEY(`id`), FOREIGN KEY(`work_id`) REFERENCES `works`(`id`) ON UPDATE NO ACTION ON DELETE CASCADE )");
        db.execSQL("CREATE INDEX IF NOT EXISTS `idx_books_work` ON `books` (`work_id`)");
        db.execSQL("CREATE TABLE IF NOT EXISTS `text_lines` (`id` INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, `book_id` TEXT NOT NULL, `line_number` INTEGER NOT NULL, `line_text` TEXT NOT NULL, `line_xml` TEXT, `speaker` TEXT, FOREIGN KEY(`book_id`) REFERENCES `books`(`id`) ON UPDATE NO ACTION ON DELETE CASCADE )");
        db.execSQL("CREATE INDEX IF NOT EXISTS `idx_text_lines_book` ON `text_lines` (`book_id`)");
        db.execSQL("CREATE TABLE IF NOT EXISTS `word_forms` (`word` TEXT NOT NULL, `word_normalized` TEXT NOT NULL, `book_id` TEXT NOT NULL, `line_number` INTEGER NOT NULL, `word_position` INTEGER NOT NULL, `char_start` INTEGER NOT NULL, `char_end` INTEGER NOT NULL, PRIMARY KEY(`book_id`, `line_number`, `word_position`), FOREIGN KEY(`book_id`) REFERENCES `books`(`id`) ON UPDATE NO ACTION ON DELETE CASCADE )");
        db.execSQL("CREATE INDEX IF NOT EXISTS `idx_word_forms_book_line` ON `word_forms` (`book_id`, `line_number`)");
        db.execSQL("CREATE INDEX IF NOT EXISTS `idx_word_forms_normalized` ON `word_forms` (`word_normalized`)");
        db.execSQL("CREATE TABLE IF NOT EXISTS `lemma_map` (`word_form` TEXT NOT NULL, `word_normalized` TEXT NOT NULL, `lemma` TEXT NOT NULL, `confidence` REAL, `source` TEXT, `morph_info` TEXT, PRIMARY KEY(`word_form`, `lemma`))");
        db.execSQL("CREATE INDEX IF NOT EXISTS `idx_lemma_map_word` ON `lemma_map` (`word_form`)");
        db.execSQL("CREATE INDEX IF NOT EXISTS `idx_lemma_map_lemma` ON `lemma_map` (`lemma`)");
        db.execSQL("CREATE TABLE IF NOT EXISTS `dictionary_entries` (`id` INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, `headword` TEXT NOT NULL, `headword_normalized` TEXT NOT NULL, `language` TEXT NOT NULL, `entry_xml` TEXT, `entry_html` TEXT, `entry_plain` TEXT, `source` TEXT)");
        db.execSQL("CREATE INDEX IF NOT EXISTS `idx_dictionary_headword_normalized` ON `dictionary_entries` (`headword_normalized`, `language`)");
        db.execSQL("CREATE TABLE IF NOT EXISTS `translation_segments` (`id` INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, `book_id` TEXT NOT NULL, `start_line` INTEGER NOT NULL, `end_line` INTEGER, `translation_text` TEXT NOT NULL, `translator` TEXT, FOREIGN KEY(`book_id`) REFERENCES `books`(`id`) ON UPDATE NO ACTION ON DELETE CASCADE )");
        db.execSQL("CREATE INDEX IF NOT EXISTS `idx_translation_segments_book` ON `translation_segments` (`book_id`)");
        db.execSQL("CREATE INDEX IF NOT EXISTS `idx_translation_segments_lines` ON `translation_segments` (`book_id`, `start_line`)");
        db.execSQL("CREATE TABLE IF NOT EXISTS room_master_table (id INTEGER PRIMARY KEY,identity_hash TEXT)");
        db.execSQL("INSERT OR REPLACE INTO room_master_table (id,identity_hash) VALUES(42, 'f5175b19ad869652c4cdf13e3f037f9d')");
      }

      @Override
      public void dropAllTables(@NonNull final SupportSQLiteDatabase db) {
        db.execSQL("DROP TABLE IF EXISTS `authors`");
        db.execSQL("DROP TABLE IF EXISTS `works`");
        db.execSQL("DROP TABLE IF EXISTS `books`");
        db.execSQL("DROP TABLE IF EXISTS `text_lines`");
        db.execSQL("DROP TABLE IF EXISTS `word_forms`");
        db.execSQL("DROP TABLE IF EXISTS `lemma_map`");
        db.execSQL("DROP TABLE IF EXISTS `dictionary_entries`");
        db.execSQL("DROP TABLE IF EXISTS `translation_segments`");
        final List<? extends RoomDatabase.Callback> _callbacks = mCallbacks;
        if (_callbacks != null) {
          for (RoomDatabase.Callback _callback : _callbacks) {
            _callback.onDestructiveMigration(db);
          }
        }
      }

      @Override
      public void onCreate(@NonNull final SupportSQLiteDatabase db) {
        final List<? extends RoomDatabase.Callback> _callbacks = mCallbacks;
        if (_callbacks != null) {
          for (RoomDatabase.Callback _callback : _callbacks) {
            _callback.onCreate(db);
          }
        }
      }

      @Override
      public void onOpen(@NonNull final SupportSQLiteDatabase db) {
        mDatabase = db;
        db.execSQL("PRAGMA foreign_keys = ON");
        internalInitInvalidationTracker(db);
        final List<? extends RoomDatabase.Callback> _callbacks = mCallbacks;
        if (_callbacks != null) {
          for (RoomDatabase.Callback _callback : _callbacks) {
            _callback.onOpen(db);
          }
        }
      }

      @Override
      public void onPreMigrate(@NonNull final SupportSQLiteDatabase db) {
        DBUtil.dropFtsSyncTriggers(db);
      }

      @Override
      public void onPostMigrate(@NonNull final SupportSQLiteDatabase db) {
      }

      @Override
      @NonNull
      public RoomOpenHelper.ValidationResult onValidateSchema(
          @NonNull final SupportSQLiteDatabase db) {
        final HashMap<String, TableInfo.Column> _columnsAuthors = new HashMap<String, TableInfo.Column>(4);
        _columnsAuthors.put("id", new TableInfo.Column("id", "TEXT", true, 1, null, TableInfo.CREATED_FROM_ENTITY));
        _columnsAuthors.put("name", new TableInfo.Column("name", "TEXT", true, 0, null, TableInfo.CREATED_FROM_ENTITY));
        _columnsAuthors.put("name_alt", new TableInfo.Column("name_alt", "TEXT", false, 0, null, TableInfo.CREATED_FROM_ENTITY));
        _columnsAuthors.put("language", new TableInfo.Column("language", "TEXT", true, 0, null, TableInfo.CREATED_FROM_ENTITY));
        final HashSet<TableInfo.ForeignKey> _foreignKeysAuthors = new HashSet<TableInfo.ForeignKey>(0);
        final HashSet<TableInfo.Index> _indicesAuthors = new HashSet<TableInfo.Index>(1);
        _indicesAuthors.add(new TableInfo.Index("idx_authors_language", false, Arrays.asList("language"), Arrays.asList("ASC")));
        final TableInfo _infoAuthors = new TableInfo("authors", _columnsAuthors, _foreignKeysAuthors, _indicesAuthors);
        final TableInfo _existingAuthors = TableInfo.read(db, "authors");
        if (!_infoAuthors.equals(_existingAuthors)) {
          return new RoomOpenHelper.ValidationResult(false, "authors(com.classicsviewer.app.database.entities.AuthorEntity).\n"
                  + " Expected:\n" + _infoAuthors + "\n"
                  + " Found:\n" + _existingAuthors);
        }
        final HashMap<String, TableInfo.Column> _columnsWorks = new HashMap<String, TableInfo.Column>(8);
        _columnsWorks.put("id", new TableInfo.Column("id", "TEXT", true, 1, null, TableInfo.CREATED_FROM_ENTITY));
        _columnsWorks.put("author_id", new TableInfo.Column("author_id", "TEXT", true, 0, null, TableInfo.CREATED_FROM_ENTITY));
        _columnsWorks.put("title", new TableInfo.Column("title", "TEXT", true, 0, null, TableInfo.CREATED_FROM_ENTITY));
        _columnsWorks.put("title_alt", new TableInfo.Column("title_alt", "TEXT", false, 0, null, TableInfo.CREATED_FROM_ENTITY));
        _columnsWorks.put("title_english", new TableInfo.Column("title_english", "TEXT", false, 0, null, TableInfo.CREATED_FROM_ENTITY));
        _columnsWorks.put("type", new TableInfo.Column("type", "TEXT", false, 0, null, TableInfo.CREATED_FROM_ENTITY));
        _columnsWorks.put("urn", new TableInfo.Column("urn", "TEXT", false, 0, null, TableInfo.CREATED_FROM_ENTITY));
        _columnsWorks.put("description", new TableInfo.Column("description", "TEXT", false, 0, null, TableInfo.CREATED_FROM_ENTITY));
        final HashSet<TableInfo.ForeignKey> _foreignKeysWorks = new HashSet<TableInfo.ForeignKey>(1);
        _foreignKeysWorks.add(new TableInfo.ForeignKey("authors", "CASCADE", "NO ACTION", Arrays.asList("author_id"), Arrays.asList("id")));
        final HashSet<TableInfo.Index> _indicesWorks = new HashSet<TableInfo.Index>(1);
        _indicesWorks.add(new TableInfo.Index("idx_works_author", false, Arrays.asList("author_id"), Arrays.asList("ASC")));
        final TableInfo _infoWorks = new TableInfo("works", _columnsWorks, _foreignKeysWorks, _indicesWorks);
        final TableInfo _existingWorks = TableInfo.read(db, "works");
        if (!_infoWorks.equals(_existingWorks)) {
          return new RoomOpenHelper.ValidationResult(false, "works(com.classicsviewer.app.database.entities.WorkEntity).\n"
                  + " Expected:\n" + _infoWorks + "\n"
                  + " Found:\n" + _existingWorks);
        }
        final HashMap<String, TableInfo.Column> _columnsBooks = new HashMap<String, TableInfo.Column>(7);
        _columnsBooks.put("id", new TableInfo.Column("id", "TEXT", true, 1, null, TableInfo.CREATED_FROM_ENTITY));
        _columnsBooks.put("work_id", new TableInfo.Column("work_id", "TEXT", true, 0, null, TableInfo.CREATED_FROM_ENTITY));
        _columnsBooks.put("book_number", new TableInfo.Column("book_number", "INTEGER", true, 0, null, TableInfo.CREATED_FROM_ENTITY));
        _columnsBooks.put("label", new TableInfo.Column("label", "TEXT", false, 0, null, TableInfo.CREATED_FROM_ENTITY));
        _columnsBooks.put("start_line", new TableInfo.Column("start_line", "INTEGER", false, 0, null, TableInfo.CREATED_FROM_ENTITY));
        _columnsBooks.put("end_line", new TableInfo.Column("end_line", "INTEGER", false, 0, null, TableInfo.CREATED_FROM_ENTITY));
        _columnsBooks.put("line_count", new TableInfo.Column("line_count", "INTEGER", false, 0, null, TableInfo.CREATED_FROM_ENTITY));
        final HashSet<TableInfo.ForeignKey> _foreignKeysBooks = new HashSet<TableInfo.ForeignKey>(1);
        _foreignKeysBooks.add(new TableInfo.ForeignKey("works", "CASCADE", "NO ACTION", Arrays.asList("work_id"), Arrays.asList("id")));
        final HashSet<TableInfo.Index> _indicesBooks = new HashSet<TableInfo.Index>(1);
        _indicesBooks.add(new TableInfo.Index("idx_books_work", false, Arrays.asList("work_id"), Arrays.asList("ASC")));
        final TableInfo _infoBooks = new TableInfo("books", _columnsBooks, _foreignKeysBooks, _indicesBooks);
        final TableInfo _existingBooks = TableInfo.read(db, "books");
        if (!_infoBooks.equals(_existingBooks)) {
          return new RoomOpenHelper.ValidationResult(false, "books(com.classicsviewer.app.database.entities.BookEntity).\n"
                  + " Expected:\n" + _infoBooks + "\n"
                  + " Found:\n" + _existingBooks);
        }
        final HashMap<String, TableInfo.Column> _columnsTextLines = new HashMap<String, TableInfo.Column>(6);
        _columnsTextLines.put("id", new TableInfo.Column("id", "INTEGER", true, 1, null, TableInfo.CREATED_FROM_ENTITY));
        _columnsTextLines.put("book_id", new TableInfo.Column("book_id", "TEXT", true, 0, null, TableInfo.CREATED_FROM_ENTITY));
        _columnsTextLines.put("line_number", new TableInfo.Column("line_number", "INTEGER", true, 0, null, TableInfo.CREATED_FROM_ENTITY));
        _columnsTextLines.put("line_text", new TableInfo.Column("line_text", "TEXT", true, 0, null, TableInfo.CREATED_FROM_ENTITY));
        _columnsTextLines.put("line_xml", new TableInfo.Column("line_xml", "TEXT", false, 0, null, TableInfo.CREATED_FROM_ENTITY));
        _columnsTextLines.put("speaker", new TableInfo.Column("speaker", "TEXT", false, 0, null, TableInfo.CREATED_FROM_ENTITY));
        final HashSet<TableInfo.ForeignKey> _foreignKeysTextLines = new HashSet<TableInfo.ForeignKey>(1);
        _foreignKeysTextLines.add(new TableInfo.ForeignKey("books", "CASCADE", "NO ACTION", Arrays.asList("book_id"), Arrays.asList("id")));
        final HashSet<TableInfo.Index> _indicesTextLines = new HashSet<TableInfo.Index>(1);
        _indicesTextLines.add(new TableInfo.Index("idx_text_lines_book", false, Arrays.asList("book_id"), Arrays.asList("ASC")));
        final TableInfo _infoTextLines = new TableInfo("text_lines", _columnsTextLines, _foreignKeysTextLines, _indicesTextLines);
        final TableInfo _existingTextLines = TableInfo.read(db, "text_lines");
        if (!_infoTextLines.equals(_existingTextLines)) {
          return new RoomOpenHelper.ValidationResult(false, "text_lines(com.classicsviewer.app.database.entities.TextLineEntity).\n"
                  + " Expected:\n" + _infoTextLines + "\n"
                  + " Found:\n" + _existingTextLines);
        }
        final HashMap<String, TableInfo.Column> _columnsWordForms = new HashMap<String, TableInfo.Column>(7);
        _columnsWordForms.put("word", new TableInfo.Column("word", "TEXT", true, 0, null, TableInfo.CREATED_FROM_ENTITY));
        _columnsWordForms.put("word_normalized", new TableInfo.Column("word_normalized", "TEXT", true, 0, null, TableInfo.CREATED_FROM_ENTITY));
        _columnsWordForms.put("book_id", new TableInfo.Column("book_id", "TEXT", true, 1, null, TableInfo.CREATED_FROM_ENTITY));
        _columnsWordForms.put("line_number", new TableInfo.Column("line_number", "INTEGER", true, 2, null, TableInfo.CREATED_FROM_ENTITY));
        _columnsWordForms.put("word_position", new TableInfo.Column("word_position", "INTEGER", true, 3, null, TableInfo.CREATED_FROM_ENTITY));
        _columnsWordForms.put("char_start", new TableInfo.Column("char_start", "INTEGER", true, 0, null, TableInfo.CREATED_FROM_ENTITY));
        _columnsWordForms.put("char_end", new TableInfo.Column("char_end", "INTEGER", true, 0, null, TableInfo.CREATED_FROM_ENTITY));
        final HashSet<TableInfo.ForeignKey> _foreignKeysWordForms = new HashSet<TableInfo.ForeignKey>(1);
        _foreignKeysWordForms.add(new TableInfo.ForeignKey("books", "CASCADE", "NO ACTION", Arrays.asList("book_id"), Arrays.asList("id")));
        final HashSet<TableInfo.Index> _indicesWordForms = new HashSet<TableInfo.Index>(2);
        _indicesWordForms.add(new TableInfo.Index("idx_word_forms_book_line", false, Arrays.asList("book_id", "line_number"), Arrays.asList("ASC", "ASC")));
        _indicesWordForms.add(new TableInfo.Index("idx_word_forms_normalized", false, Arrays.asList("word_normalized"), Arrays.asList("ASC")));
        final TableInfo _infoWordForms = new TableInfo("word_forms", _columnsWordForms, _foreignKeysWordForms, _indicesWordForms);
        final TableInfo _existingWordForms = TableInfo.read(db, "word_forms");
        if (!_infoWordForms.equals(_existingWordForms)) {
          return new RoomOpenHelper.ValidationResult(false, "word_forms(com.classicsviewer.app.database.entities.WordFormEntity).\n"
                  + " Expected:\n" + _infoWordForms + "\n"
                  + " Found:\n" + _existingWordForms);
        }
        final HashMap<String, TableInfo.Column> _columnsLemmaMap = new HashMap<String, TableInfo.Column>(6);
        _columnsLemmaMap.put("word_form", new TableInfo.Column("word_form", "TEXT", true, 1, null, TableInfo.CREATED_FROM_ENTITY));
        _columnsLemmaMap.put("word_normalized", new TableInfo.Column("word_normalized", "TEXT", true, 0, null, TableInfo.CREATED_FROM_ENTITY));
        _columnsLemmaMap.put("lemma", new TableInfo.Column("lemma", "TEXT", true, 2, null, TableInfo.CREATED_FROM_ENTITY));
        _columnsLemmaMap.put("confidence", new TableInfo.Column("confidence", "REAL", false, 0, null, TableInfo.CREATED_FROM_ENTITY));
        _columnsLemmaMap.put("source", new TableInfo.Column("source", "TEXT", false, 0, null, TableInfo.CREATED_FROM_ENTITY));
        _columnsLemmaMap.put("morph_info", new TableInfo.Column("morph_info", "TEXT", false, 0, null, TableInfo.CREATED_FROM_ENTITY));
        final HashSet<TableInfo.ForeignKey> _foreignKeysLemmaMap = new HashSet<TableInfo.ForeignKey>(0);
        final HashSet<TableInfo.Index> _indicesLemmaMap = new HashSet<TableInfo.Index>(2);
        _indicesLemmaMap.add(new TableInfo.Index("idx_lemma_map_word", false, Arrays.asList("word_form"), Arrays.asList("ASC")));
        _indicesLemmaMap.add(new TableInfo.Index("idx_lemma_map_lemma", false, Arrays.asList("lemma"), Arrays.asList("ASC")));
        final TableInfo _infoLemmaMap = new TableInfo("lemma_map", _columnsLemmaMap, _foreignKeysLemmaMap, _indicesLemmaMap);
        final TableInfo _existingLemmaMap = TableInfo.read(db, "lemma_map");
        if (!_infoLemmaMap.equals(_existingLemmaMap)) {
          return new RoomOpenHelper.ValidationResult(false, "lemma_map(com.classicsviewer.app.database.entities.LemmaMapEntity).\n"
                  + " Expected:\n" + _infoLemmaMap + "\n"
                  + " Found:\n" + _existingLemmaMap);
        }
        final HashMap<String, TableInfo.Column> _columnsDictionaryEntries = new HashMap<String, TableInfo.Column>(8);
        _columnsDictionaryEntries.put("id", new TableInfo.Column("id", "INTEGER", true, 1, null, TableInfo.CREATED_FROM_ENTITY));
        _columnsDictionaryEntries.put("headword", new TableInfo.Column("headword", "TEXT", true, 0, null, TableInfo.CREATED_FROM_ENTITY));
        _columnsDictionaryEntries.put("headword_normalized", new TableInfo.Column("headword_normalized", "TEXT", true, 0, null, TableInfo.CREATED_FROM_ENTITY));
        _columnsDictionaryEntries.put("language", new TableInfo.Column("language", "TEXT", true, 0, null, TableInfo.CREATED_FROM_ENTITY));
        _columnsDictionaryEntries.put("entry_xml", new TableInfo.Column("entry_xml", "TEXT", false, 0, null, TableInfo.CREATED_FROM_ENTITY));
        _columnsDictionaryEntries.put("entry_html", new TableInfo.Column("entry_html", "TEXT", false, 0, null, TableInfo.CREATED_FROM_ENTITY));
        _columnsDictionaryEntries.put("entry_plain", new TableInfo.Column("entry_plain", "TEXT", false, 0, null, TableInfo.CREATED_FROM_ENTITY));
        _columnsDictionaryEntries.put("source", new TableInfo.Column("source", "TEXT", false, 0, null, TableInfo.CREATED_FROM_ENTITY));
        final HashSet<TableInfo.ForeignKey> _foreignKeysDictionaryEntries = new HashSet<TableInfo.ForeignKey>(0);
        final HashSet<TableInfo.Index> _indicesDictionaryEntries = new HashSet<TableInfo.Index>(1);
        _indicesDictionaryEntries.add(new TableInfo.Index("idx_dictionary_headword_normalized", false, Arrays.asList("headword_normalized", "language"), Arrays.asList("ASC", "ASC")));
        final TableInfo _infoDictionaryEntries = new TableInfo("dictionary_entries", _columnsDictionaryEntries, _foreignKeysDictionaryEntries, _indicesDictionaryEntries);
        final TableInfo _existingDictionaryEntries = TableInfo.read(db, "dictionary_entries");
        if (!_infoDictionaryEntries.equals(_existingDictionaryEntries)) {
          return new RoomOpenHelper.ValidationResult(false, "dictionary_entries(com.classicsviewer.app.database.entities.DictionaryEntity).\n"
                  + " Expected:\n" + _infoDictionaryEntries + "\n"
                  + " Found:\n" + _existingDictionaryEntries);
        }
        final HashMap<String, TableInfo.Column> _columnsTranslationSegments = new HashMap<String, TableInfo.Column>(6);
        _columnsTranslationSegments.put("id", new TableInfo.Column("id", "INTEGER", true, 1, null, TableInfo.CREATED_FROM_ENTITY));
        _columnsTranslationSegments.put("book_id", new TableInfo.Column("book_id", "TEXT", true, 0, null, TableInfo.CREATED_FROM_ENTITY));
        _columnsTranslationSegments.put("start_line", new TableInfo.Column("start_line", "INTEGER", true, 0, null, TableInfo.CREATED_FROM_ENTITY));
        _columnsTranslationSegments.put("end_line", new TableInfo.Column("end_line", "INTEGER", false, 0, null, TableInfo.CREATED_FROM_ENTITY));
        _columnsTranslationSegments.put("translation_text", new TableInfo.Column("translation_text", "TEXT", true, 0, null, TableInfo.CREATED_FROM_ENTITY));
        _columnsTranslationSegments.put("translator", new TableInfo.Column("translator", "TEXT", false, 0, null, TableInfo.CREATED_FROM_ENTITY));
        final HashSet<TableInfo.ForeignKey> _foreignKeysTranslationSegments = new HashSet<TableInfo.ForeignKey>(1);
        _foreignKeysTranslationSegments.add(new TableInfo.ForeignKey("books", "CASCADE", "NO ACTION", Arrays.asList("book_id"), Arrays.asList("id")));
        final HashSet<TableInfo.Index> _indicesTranslationSegments = new HashSet<TableInfo.Index>(2);
        _indicesTranslationSegments.add(new TableInfo.Index("idx_translation_segments_book", false, Arrays.asList("book_id"), Arrays.asList("ASC")));
        _indicesTranslationSegments.add(new TableInfo.Index("idx_translation_segments_lines", false, Arrays.asList("book_id", "start_line"), Arrays.asList("ASC", "ASC")));
        final TableInfo _infoTranslationSegments = new TableInfo("translation_segments", _columnsTranslationSegments, _foreignKeysTranslationSegments, _indicesTranslationSegments);
        final TableInfo _existingTranslationSegments = TableInfo.read(db, "translation_segments");
        if (!_infoTranslationSegments.equals(_existingTranslationSegments)) {
          return new RoomOpenHelper.ValidationResult(false, "translation_segments(com.classicsviewer.app.database.entities.TranslationSegmentEntity).\n"
                  + " Expected:\n" + _infoTranslationSegments + "\n"
                  + " Found:\n" + _existingTranslationSegments);
        }
        return new RoomOpenHelper.ValidationResult(true, null);
      }
    }, "f5175b19ad869652c4cdf13e3f037f9d", "b2923d2217679fc43d46c7ea5069e71c");
    final SupportSQLiteOpenHelper.Configuration _sqliteConfig = SupportSQLiteOpenHelper.Configuration.builder(config.context).name(config.name).callback(_openCallback).build();
    final SupportSQLiteOpenHelper _helper = config.sqliteOpenHelperFactory.create(_sqliteConfig);
    return _helper;
  }

  @Override
  @NonNull
  protected InvalidationTracker createInvalidationTracker() {
    final HashMap<String, String> _shadowTablesMap = new HashMap<String, String>(0);
    final HashMap<String, Set<String>> _viewTables = new HashMap<String, Set<String>>(0);
    return new InvalidationTracker(this, _shadowTablesMap, _viewTables, "authors","works","books","text_lines","word_forms","lemma_map","dictionary_entries","translation_segments");
  }

  @Override
  public void clearAllTables() {
    super.assertNotMainThread();
    final SupportSQLiteDatabase _db = super.getOpenHelper().getWritableDatabase();
    final boolean _supportsDeferForeignKeys = android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.LOLLIPOP;
    try {
      if (!_supportsDeferForeignKeys) {
        _db.execSQL("PRAGMA foreign_keys = FALSE");
      }
      super.beginTransaction();
      if (_supportsDeferForeignKeys) {
        _db.execSQL("PRAGMA defer_foreign_keys = TRUE");
      }
      _db.execSQL("DELETE FROM `authors`");
      _db.execSQL("DELETE FROM `works`");
      _db.execSQL("DELETE FROM `books`");
      _db.execSQL("DELETE FROM `text_lines`");
      _db.execSQL("DELETE FROM `word_forms`");
      _db.execSQL("DELETE FROM `lemma_map`");
      _db.execSQL("DELETE FROM `dictionary_entries`");
      _db.execSQL("DELETE FROM `translation_segments`");
      super.setTransactionSuccessful();
    } finally {
      super.endTransaction();
      if (!_supportsDeferForeignKeys) {
        _db.execSQL("PRAGMA foreign_keys = TRUE");
      }
      _db.query("PRAGMA wal_checkpoint(FULL)").close();
      if (!_db.inTransaction()) {
        _db.execSQL("VACUUM");
      }
    }
  }

  @Override
  @NonNull
  protected Map<Class<?>, List<Class<?>>> getRequiredTypeConverters() {
    final HashMap<Class<?>, List<Class<?>>> _typeConvertersMap = new HashMap<Class<?>, List<Class<?>>>();
    _typeConvertersMap.put(AuthorDao.class, AuthorDao_Impl.getRequiredConverters());
    _typeConvertersMap.put(WorkDao.class, WorkDao_Impl.getRequiredConverters());
    _typeConvertersMap.put(BookDao.class, BookDao_Impl.getRequiredConverters());
    _typeConvertersMap.put(TextLineDao.class, TextLineDao_Impl.getRequiredConverters());
    _typeConvertersMap.put(WordFormDao.class, WordFormDao_Impl.getRequiredConverters());
    _typeConvertersMap.put(LemmaDao.class, LemmaDao_Impl.getRequiredConverters());
    _typeConvertersMap.put(LemmaMapDao.class, LemmaMapDao_Impl.getRequiredConverters());
    _typeConvertersMap.put(DictionaryDao.class, DictionaryDao_Impl.getRequiredConverters());
    _typeConvertersMap.put(TranslationSegmentDao.class, TranslationSegmentDao_Impl.getRequiredConverters());
    return _typeConvertersMap;
  }

  @Override
  @NonNull
  public Set<Class<? extends AutoMigrationSpec>> getRequiredAutoMigrationSpecs() {
    final HashSet<Class<? extends AutoMigrationSpec>> _autoMigrationSpecsSet = new HashSet<Class<? extends AutoMigrationSpec>>();
    return _autoMigrationSpecsSet;
  }

  @Override
  @NonNull
  public List<Migration> getAutoMigrations(
      @NonNull final Map<Class<? extends AutoMigrationSpec>, AutoMigrationSpec> autoMigrationSpecs) {
    final List<Migration> _autoMigrations = new ArrayList<Migration>();
    return _autoMigrations;
  }

  @Override
  public AuthorDao authorDao() {
    if (_authorDao != null) {
      return _authorDao;
    } else {
      synchronized(this) {
        if(_authorDao == null) {
          _authorDao = new AuthorDao_Impl(this);
        }
        return _authorDao;
      }
    }
  }

  @Override
  public WorkDao workDao() {
    if (_workDao != null) {
      return _workDao;
    } else {
      synchronized(this) {
        if(_workDao == null) {
          _workDao = new WorkDao_Impl(this);
        }
        return _workDao;
      }
    }
  }

  @Override
  public BookDao bookDao() {
    if (_bookDao != null) {
      return _bookDao;
    } else {
      synchronized(this) {
        if(_bookDao == null) {
          _bookDao = new BookDao_Impl(this);
        }
        return _bookDao;
      }
    }
  }

  @Override
  public TextLineDao textLineDao() {
    if (_textLineDao != null) {
      return _textLineDao;
    } else {
      synchronized(this) {
        if(_textLineDao == null) {
          _textLineDao = new TextLineDao_Impl(this);
        }
        return _textLineDao;
      }
    }
  }

  @Override
  public WordFormDao wordFormDao() {
    if (_wordFormDao != null) {
      return _wordFormDao;
    } else {
      synchronized(this) {
        if(_wordFormDao == null) {
          _wordFormDao = new WordFormDao_Impl(this);
        }
        return _wordFormDao;
      }
    }
  }

  @Override
  public LemmaDao lemmaDao() {
    if (_lemmaDao != null) {
      return _lemmaDao;
    } else {
      synchronized(this) {
        if(_lemmaDao == null) {
          _lemmaDao = new LemmaDao_Impl(this);
        }
        return _lemmaDao;
      }
    }
  }

  @Override
  public LemmaMapDao lemmaMapDao() {
    if (_lemmaMapDao != null) {
      return _lemmaMapDao;
    } else {
      synchronized(this) {
        if(_lemmaMapDao == null) {
          _lemmaMapDao = new LemmaMapDao_Impl(this);
        }
        return _lemmaMapDao;
      }
    }
  }

  @Override
  public DictionaryDao dictionaryDao() {
    if (_dictionaryDao != null) {
      return _dictionaryDao;
    } else {
      synchronized(this) {
        if(_dictionaryDao == null) {
          _dictionaryDao = new DictionaryDao_Impl(this);
        }
        return _dictionaryDao;
      }
    }
  }

  @Override
  public TranslationSegmentDao translationSegmentDao() {
    if (_translationSegmentDao != null) {
      return _translationSegmentDao;
    } else {
      synchronized(this) {
        if(_translationSegmentDao == null) {
          _translationSegmentDao = new TranslationSegmentDao_Impl(this);
        }
        return _translationSegmentDao;
      }
    }
  }
}

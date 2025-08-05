package com.classicsviewer.app.database.dao;

import android.database.Cursor;
import android.os.CancellationSignal;
import androidx.annotation.NonNull;
import androidx.annotation.Nullable;
import androidx.room.CoroutinesRoom;
import androidx.room.RoomDatabase;
import androidx.room.RoomSQLiteQuery;
import androidx.room.util.CursorUtil;
import androidx.room.util.DBUtil;
import com.classicsviewer.app.database.entities.DictionaryEntity;
import java.lang.Class;
import java.lang.Exception;
import java.lang.Integer;
import java.lang.Object;
import java.lang.Override;
import java.lang.String;
import java.lang.SuppressWarnings;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.concurrent.Callable;
import javax.annotation.processing.Generated;
import kotlin.coroutines.Continuation;

@Generated("androidx.room.RoomProcessor")
@SuppressWarnings({"unchecked", "deprecation"})
public final class DictionaryDao_Impl implements DictionaryDao {
  private final RoomDatabase __db;

  public DictionaryDao_Impl(@NonNull final RoomDatabase __db) {
    this.__db = __db;
  }

  @Override
  public Object getEntry(final String headword, final String language,
      final Continuation<? super DictionaryEntity> $completion) {
    final String _sql = "SELECT * FROM dictionary_entries WHERE headword_normalized = ? AND language = ? LIMIT 1";
    final RoomSQLiteQuery _statement = RoomSQLiteQuery.acquire(_sql, 2);
    int _argIndex = 1;
    if (headword == null) {
      _statement.bindNull(_argIndex);
    } else {
      _statement.bindString(_argIndex, headword);
    }
    _argIndex = 2;
    if (language == null) {
      _statement.bindNull(_argIndex);
    } else {
      _statement.bindString(_argIndex, language);
    }
    final CancellationSignal _cancellationSignal = DBUtil.createCancellationSignal();
    return CoroutinesRoom.execute(__db, false, _cancellationSignal, new Callable<DictionaryEntity>() {
      @Override
      @Nullable
      public DictionaryEntity call() throws Exception {
        final Cursor _cursor = DBUtil.query(__db, _statement, false, null);
        try {
          final int _cursorIndexOfId = CursorUtil.getColumnIndexOrThrow(_cursor, "id");
          final int _cursorIndexOfHeadword = CursorUtil.getColumnIndexOrThrow(_cursor, "headword");
          final int _cursorIndexOfHeadwordNormalized = CursorUtil.getColumnIndexOrThrow(_cursor, "headword_normalized");
          final int _cursorIndexOfLanguage = CursorUtil.getColumnIndexOrThrow(_cursor, "language");
          final int _cursorIndexOfEntryXml = CursorUtil.getColumnIndexOrThrow(_cursor, "entry_xml");
          final int _cursorIndexOfEntryHtml = CursorUtil.getColumnIndexOrThrow(_cursor, "entry_html");
          final int _cursorIndexOfEntryPlain = CursorUtil.getColumnIndexOrThrow(_cursor, "entry_plain");
          final int _cursorIndexOfSource = CursorUtil.getColumnIndexOrThrow(_cursor, "source");
          final DictionaryEntity _result;
          if (_cursor.moveToFirst()) {
            final int _tmpId;
            _tmpId = _cursor.getInt(_cursorIndexOfId);
            final String _tmpHeadword;
            if (_cursor.isNull(_cursorIndexOfHeadword)) {
              _tmpHeadword = null;
            } else {
              _tmpHeadword = _cursor.getString(_cursorIndexOfHeadword);
            }
            final String _tmpHeadwordNormalized;
            if (_cursor.isNull(_cursorIndexOfHeadwordNormalized)) {
              _tmpHeadwordNormalized = null;
            } else {
              _tmpHeadwordNormalized = _cursor.getString(_cursorIndexOfHeadwordNormalized);
            }
            final String _tmpLanguage;
            if (_cursor.isNull(_cursorIndexOfLanguage)) {
              _tmpLanguage = null;
            } else {
              _tmpLanguage = _cursor.getString(_cursorIndexOfLanguage);
            }
            final String _tmpEntryXml;
            if (_cursor.isNull(_cursorIndexOfEntryXml)) {
              _tmpEntryXml = null;
            } else {
              _tmpEntryXml = _cursor.getString(_cursorIndexOfEntryXml);
            }
            final String _tmpEntryHtml;
            if (_cursor.isNull(_cursorIndexOfEntryHtml)) {
              _tmpEntryHtml = null;
            } else {
              _tmpEntryHtml = _cursor.getString(_cursorIndexOfEntryHtml);
            }
            final String _tmpEntryPlain;
            if (_cursor.isNull(_cursorIndexOfEntryPlain)) {
              _tmpEntryPlain = null;
            } else {
              _tmpEntryPlain = _cursor.getString(_cursorIndexOfEntryPlain);
            }
            final String _tmpSource;
            if (_cursor.isNull(_cursorIndexOfSource)) {
              _tmpSource = null;
            } else {
              _tmpSource = _cursor.getString(_cursorIndexOfSource);
            }
            _result = new DictionaryEntity(_tmpId,_tmpHeadword,_tmpHeadwordNormalized,_tmpLanguage,_tmpEntryXml,_tmpEntryHtml,_tmpEntryPlain,_tmpSource);
          } else {
            _result = null;
          }
          return _result;
        } finally {
          _cursor.close();
          _statement.release();
        }
      }
    }, $completion);
  }

  @Override
  public Object getEntryCount(final String language,
      final Continuation<? super Integer> $completion) {
    final String _sql = "SELECT COUNT(*) FROM dictionary_entries WHERE language = ?";
    final RoomSQLiteQuery _statement = RoomSQLiteQuery.acquire(_sql, 1);
    int _argIndex = 1;
    if (language == null) {
      _statement.bindNull(_argIndex);
    } else {
      _statement.bindString(_argIndex, language);
    }
    final CancellationSignal _cancellationSignal = DBUtil.createCancellationSignal();
    return CoroutinesRoom.execute(__db, false, _cancellationSignal, new Callable<Integer>() {
      @Override
      @NonNull
      public Integer call() throws Exception {
        final Cursor _cursor = DBUtil.query(__db, _statement, false, null);
        try {
          final Integer _result;
          if (_cursor.moveToFirst()) {
            final Integer _tmp;
            if (_cursor.isNull(0)) {
              _tmp = null;
            } else {
              _tmp = _cursor.getInt(0);
            }
            _result = _tmp;
          } else {
            _result = null;
          }
          return _result;
        } finally {
          _cursor.close();
          _statement.release();
        }
      }
    }, $completion);
  }

  @Override
  public Object searchEntries(final String pattern, final String language, final int limit,
      final Continuation<? super List<DictionaryEntity>> $completion) {
    final String _sql = "SELECT * FROM dictionary_entries WHERE headword_normalized LIKE ? AND language = ? LIMIT ?";
    final RoomSQLiteQuery _statement = RoomSQLiteQuery.acquire(_sql, 3);
    int _argIndex = 1;
    if (pattern == null) {
      _statement.bindNull(_argIndex);
    } else {
      _statement.bindString(_argIndex, pattern);
    }
    _argIndex = 2;
    if (language == null) {
      _statement.bindNull(_argIndex);
    } else {
      _statement.bindString(_argIndex, language);
    }
    _argIndex = 3;
    _statement.bindLong(_argIndex, limit);
    final CancellationSignal _cancellationSignal = DBUtil.createCancellationSignal();
    return CoroutinesRoom.execute(__db, false, _cancellationSignal, new Callable<List<DictionaryEntity>>() {
      @Override
      @NonNull
      public List<DictionaryEntity> call() throws Exception {
        final Cursor _cursor = DBUtil.query(__db, _statement, false, null);
        try {
          final int _cursorIndexOfId = CursorUtil.getColumnIndexOrThrow(_cursor, "id");
          final int _cursorIndexOfHeadword = CursorUtil.getColumnIndexOrThrow(_cursor, "headword");
          final int _cursorIndexOfHeadwordNormalized = CursorUtil.getColumnIndexOrThrow(_cursor, "headword_normalized");
          final int _cursorIndexOfLanguage = CursorUtil.getColumnIndexOrThrow(_cursor, "language");
          final int _cursorIndexOfEntryXml = CursorUtil.getColumnIndexOrThrow(_cursor, "entry_xml");
          final int _cursorIndexOfEntryHtml = CursorUtil.getColumnIndexOrThrow(_cursor, "entry_html");
          final int _cursorIndexOfEntryPlain = CursorUtil.getColumnIndexOrThrow(_cursor, "entry_plain");
          final int _cursorIndexOfSource = CursorUtil.getColumnIndexOrThrow(_cursor, "source");
          final List<DictionaryEntity> _result = new ArrayList<DictionaryEntity>(_cursor.getCount());
          while (_cursor.moveToNext()) {
            final DictionaryEntity _item;
            final int _tmpId;
            _tmpId = _cursor.getInt(_cursorIndexOfId);
            final String _tmpHeadword;
            if (_cursor.isNull(_cursorIndexOfHeadword)) {
              _tmpHeadword = null;
            } else {
              _tmpHeadword = _cursor.getString(_cursorIndexOfHeadword);
            }
            final String _tmpHeadwordNormalized;
            if (_cursor.isNull(_cursorIndexOfHeadwordNormalized)) {
              _tmpHeadwordNormalized = null;
            } else {
              _tmpHeadwordNormalized = _cursor.getString(_cursorIndexOfHeadwordNormalized);
            }
            final String _tmpLanguage;
            if (_cursor.isNull(_cursorIndexOfLanguage)) {
              _tmpLanguage = null;
            } else {
              _tmpLanguage = _cursor.getString(_cursorIndexOfLanguage);
            }
            final String _tmpEntryXml;
            if (_cursor.isNull(_cursorIndexOfEntryXml)) {
              _tmpEntryXml = null;
            } else {
              _tmpEntryXml = _cursor.getString(_cursorIndexOfEntryXml);
            }
            final String _tmpEntryHtml;
            if (_cursor.isNull(_cursorIndexOfEntryHtml)) {
              _tmpEntryHtml = null;
            } else {
              _tmpEntryHtml = _cursor.getString(_cursorIndexOfEntryHtml);
            }
            final String _tmpEntryPlain;
            if (_cursor.isNull(_cursorIndexOfEntryPlain)) {
              _tmpEntryPlain = null;
            } else {
              _tmpEntryPlain = _cursor.getString(_cursorIndexOfEntryPlain);
            }
            final String _tmpSource;
            if (_cursor.isNull(_cursorIndexOfSource)) {
              _tmpSource = null;
            } else {
              _tmpSource = _cursor.getString(_cursorIndexOfSource);
            }
            _item = new DictionaryEntity(_tmpId,_tmpHeadword,_tmpHeadwordNormalized,_tmpLanguage,_tmpEntryXml,_tmpEntryHtml,_tmpEntryPlain,_tmpSource);
            _result.add(_item);
          }
          return _result;
        } finally {
          _cursor.close();
          _statement.release();
        }
      }
    }, $completion);
  }

  @NonNull
  public static List<Class<?>> getRequiredConverters() {
    return Collections.emptyList();
  }
}

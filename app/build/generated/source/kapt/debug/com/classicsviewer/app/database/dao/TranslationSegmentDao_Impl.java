package com.classicsviewer.app.database.dao;

import android.database.Cursor;
import android.os.CancellationSignal;
import androidx.annotation.NonNull;
import androidx.room.CoroutinesRoom;
import androidx.room.RoomDatabase;
import androidx.room.RoomSQLiteQuery;
import androidx.room.util.CursorUtil;
import androidx.room.util.DBUtil;
import com.classicsviewer.app.database.entities.TranslationSegmentEntity;
import java.lang.Boolean;
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
public final class TranslationSegmentDao_Impl implements TranslationSegmentDao {
  private final RoomDatabase __db;

  public TranslationSegmentDao_Impl(@NonNull final RoomDatabase __db) {
    this.__db = __db;
  }

  @Override
  public Object getTranslationSegments(final String bookId, final int startLine, final int endLine,
      final Continuation<? super List<TranslationSegmentEntity>> $completion) {
    final String _sql = "\n"
            + "        SELECT * FROM translation_segments \n"
            + "        WHERE book_id = ? \n"
            + "        AND start_line <= ? \n"
            + "        AND (end_line IS NULL OR end_line >= ?)\n"
            + "        ORDER BY start_line\n"
            + "    ";
    final RoomSQLiteQuery _statement = RoomSQLiteQuery.acquire(_sql, 3);
    int _argIndex = 1;
    if (bookId == null) {
      _statement.bindNull(_argIndex);
    } else {
      _statement.bindString(_argIndex, bookId);
    }
    _argIndex = 2;
    _statement.bindLong(_argIndex, endLine);
    _argIndex = 3;
    _statement.bindLong(_argIndex, startLine);
    final CancellationSignal _cancellationSignal = DBUtil.createCancellationSignal();
    return CoroutinesRoom.execute(__db, false, _cancellationSignal, new Callable<List<TranslationSegmentEntity>>() {
      @Override
      @NonNull
      public List<TranslationSegmentEntity> call() throws Exception {
        final Cursor _cursor = DBUtil.query(__db, _statement, false, null);
        try {
          final int _cursorIndexOfId = CursorUtil.getColumnIndexOrThrow(_cursor, "id");
          final int _cursorIndexOfBookId = CursorUtil.getColumnIndexOrThrow(_cursor, "book_id");
          final int _cursorIndexOfStartLine = CursorUtil.getColumnIndexOrThrow(_cursor, "start_line");
          final int _cursorIndexOfEndLine = CursorUtil.getColumnIndexOrThrow(_cursor, "end_line");
          final int _cursorIndexOfTranslationText = CursorUtil.getColumnIndexOrThrow(_cursor, "translation_text");
          final int _cursorIndexOfTranslator = CursorUtil.getColumnIndexOrThrow(_cursor, "translator");
          final List<TranslationSegmentEntity> _result = new ArrayList<TranslationSegmentEntity>(_cursor.getCount());
          while (_cursor.moveToNext()) {
            final TranslationSegmentEntity _item;
            final long _tmpId;
            _tmpId = _cursor.getLong(_cursorIndexOfId);
            final String _tmpBookId;
            if (_cursor.isNull(_cursorIndexOfBookId)) {
              _tmpBookId = null;
            } else {
              _tmpBookId = _cursor.getString(_cursorIndexOfBookId);
            }
            final int _tmpStartLine;
            _tmpStartLine = _cursor.getInt(_cursorIndexOfStartLine);
            final Integer _tmpEndLine;
            if (_cursor.isNull(_cursorIndexOfEndLine)) {
              _tmpEndLine = null;
            } else {
              _tmpEndLine = _cursor.getInt(_cursorIndexOfEndLine);
            }
            final String _tmpTranslationText;
            if (_cursor.isNull(_cursorIndexOfTranslationText)) {
              _tmpTranslationText = null;
            } else {
              _tmpTranslationText = _cursor.getString(_cursorIndexOfTranslationText);
            }
            final String _tmpTranslator;
            if (_cursor.isNull(_cursorIndexOfTranslator)) {
              _tmpTranslator = null;
            } else {
              _tmpTranslator = _cursor.getString(_cursorIndexOfTranslator);
            }
            _item = new TranslationSegmentEntity(_tmpId,_tmpBookId,_tmpStartLine,_tmpEndLine,_tmpTranslationText,_tmpTranslator);
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

  @Override
  public Object getAllTranslationSegments(final String bookId,
      final Continuation<? super List<TranslationSegmentEntity>> $completion) {
    final String _sql = "SELECT * FROM translation_segments WHERE book_id = ? ORDER BY start_line";
    final RoomSQLiteQuery _statement = RoomSQLiteQuery.acquire(_sql, 1);
    int _argIndex = 1;
    if (bookId == null) {
      _statement.bindNull(_argIndex);
    } else {
      _statement.bindString(_argIndex, bookId);
    }
    final CancellationSignal _cancellationSignal = DBUtil.createCancellationSignal();
    return CoroutinesRoom.execute(__db, false, _cancellationSignal, new Callable<List<TranslationSegmentEntity>>() {
      @Override
      @NonNull
      public List<TranslationSegmentEntity> call() throws Exception {
        final Cursor _cursor = DBUtil.query(__db, _statement, false, null);
        try {
          final int _cursorIndexOfId = CursorUtil.getColumnIndexOrThrow(_cursor, "id");
          final int _cursorIndexOfBookId = CursorUtil.getColumnIndexOrThrow(_cursor, "book_id");
          final int _cursorIndexOfStartLine = CursorUtil.getColumnIndexOrThrow(_cursor, "start_line");
          final int _cursorIndexOfEndLine = CursorUtil.getColumnIndexOrThrow(_cursor, "end_line");
          final int _cursorIndexOfTranslationText = CursorUtil.getColumnIndexOrThrow(_cursor, "translation_text");
          final int _cursorIndexOfTranslator = CursorUtil.getColumnIndexOrThrow(_cursor, "translator");
          final List<TranslationSegmentEntity> _result = new ArrayList<TranslationSegmentEntity>(_cursor.getCount());
          while (_cursor.moveToNext()) {
            final TranslationSegmentEntity _item;
            final long _tmpId;
            _tmpId = _cursor.getLong(_cursorIndexOfId);
            final String _tmpBookId;
            if (_cursor.isNull(_cursorIndexOfBookId)) {
              _tmpBookId = null;
            } else {
              _tmpBookId = _cursor.getString(_cursorIndexOfBookId);
            }
            final int _tmpStartLine;
            _tmpStartLine = _cursor.getInt(_cursorIndexOfStartLine);
            final Integer _tmpEndLine;
            if (_cursor.isNull(_cursorIndexOfEndLine)) {
              _tmpEndLine = null;
            } else {
              _tmpEndLine = _cursor.getInt(_cursorIndexOfEndLine);
            }
            final String _tmpTranslationText;
            if (_cursor.isNull(_cursorIndexOfTranslationText)) {
              _tmpTranslationText = null;
            } else {
              _tmpTranslationText = _cursor.getString(_cursorIndexOfTranslationText);
            }
            final String _tmpTranslator;
            if (_cursor.isNull(_cursorIndexOfTranslator)) {
              _tmpTranslator = null;
            } else {
              _tmpTranslator = _cursor.getString(_cursorIndexOfTranslator);
            }
            _item = new TranslationSegmentEntity(_tmpId,_tmpBookId,_tmpStartLine,_tmpEndLine,_tmpTranslationText,_tmpTranslator);
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

  @Override
  public Object getTranslationCount(final String bookId,
      final Continuation<? super Integer> $completion) {
    final String _sql = "SELECT COUNT(*) FROM translation_segments WHERE book_id = ?";
    final RoomSQLiteQuery _statement = RoomSQLiteQuery.acquire(_sql, 1);
    int _argIndex = 1;
    if (bookId == null) {
      _statement.bindNull(_argIndex);
    } else {
      _statement.bindString(_argIndex, bookId);
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
  public Object getAvailableTranslators(final String bookId,
      final Continuation<? super List<String>> $completion) {
    final String _sql = "SELECT DISTINCT translator FROM translation_segments WHERE book_id = ? AND translator IS NOT NULL ORDER BY translator";
    final RoomSQLiteQuery _statement = RoomSQLiteQuery.acquire(_sql, 1);
    int _argIndex = 1;
    if (bookId == null) {
      _statement.bindNull(_argIndex);
    } else {
      _statement.bindString(_argIndex, bookId);
    }
    final CancellationSignal _cancellationSignal = DBUtil.createCancellationSignal();
    return CoroutinesRoom.execute(__db, false, _cancellationSignal, new Callable<List<String>>() {
      @Override
      @NonNull
      public List<String> call() throws Exception {
        final Cursor _cursor = DBUtil.query(__db, _statement, false, null);
        try {
          final List<String> _result = new ArrayList<String>(_cursor.getCount());
          while (_cursor.moveToNext()) {
            final String _item;
            if (_cursor.isNull(0)) {
              _item = null;
            } else {
              _item = _cursor.getString(0);
            }
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

  @Override
  public Object getTranslationSegmentsByTranslator(final String bookId, final String translator,
      final int startLine, final int endLine,
      final Continuation<? super List<TranslationSegmentEntity>> $completion) {
    final String _sql = "\n"
            + "        SELECT * FROM translation_segments \n"
            + "        WHERE book_id = ? \n"
            + "        AND translator = ?\n"
            + "        AND start_line <= ? \n"
            + "        AND (end_line IS NULL OR end_line >= ?)\n"
            + "        ORDER BY start_line\n"
            + "    ";
    final RoomSQLiteQuery _statement = RoomSQLiteQuery.acquire(_sql, 4);
    int _argIndex = 1;
    if (bookId == null) {
      _statement.bindNull(_argIndex);
    } else {
      _statement.bindString(_argIndex, bookId);
    }
    _argIndex = 2;
    if (translator == null) {
      _statement.bindNull(_argIndex);
    } else {
      _statement.bindString(_argIndex, translator);
    }
    _argIndex = 3;
    _statement.bindLong(_argIndex, endLine);
    _argIndex = 4;
    _statement.bindLong(_argIndex, startLine);
    final CancellationSignal _cancellationSignal = DBUtil.createCancellationSignal();
    return CoroutinesRoom.execute(__db, false, _cancellationSignal, new Callable<List<TranslationSegmentEntity>>() {
      @Override
      @NonNull
      public List<TranslationSegmentEntity> call() throws Exception {
        final Cursor _cursor = DBUtil.query(__db, _statement, false, null);
        try {
          final int _cursorIndexOfId = CursorUtil.getColumnIndexOrThrow(_cursor, "id");
          final int _cursorIndexOfBookId = CursorUtil.getColumnIndexOrThrow(_cursor, "book_id");
          final int _cursorIndexOfStartLine = CursorUtil.getColumnIndexOrThrow(_cursor, "start_line");
          final int _cursorIndexOfEndLine = CursorUtil.getColumnIndexOrThrow(_cursor, "end_line");
          final int _cursorIndexOfTranslationText = CursorUtil.getColumnIndexOrThrow(_cursor, "translation_text");
          final int _cursorIndexOfTranslator = CursorUtil.getColumnIndexOrThrow(_cursor, "translator");
          final List<TranslationSegmentEntity> _result = new ArrayList<TranslationSegmentEntity>(_cursor.getCount());
          while (_cursor.moveToNext()) {
            final TranslationSegmentEntity _item;
            final long _tmpId;
            _tmpId = _cursor.getLong(_cursorIndexOfId);
            final String _tmpBookId;
            if (_cursor.isNull(_cursorIndexOfBookId)) {
              _tmpBookId = null;
            } else {
              _tmpBookId = _cursor.getString(_cursorIndexOfBookId);
            }
            final int _tmpStartLine;
            _tmpStartLine = _cursor.getInt(_cursorIndexOfStartLine);
            final Integer _tmpEndLine;
            if (_cursor.isNull(_cursorIndexOfEndLine)) {
              _tmpEndLine = null;
            } else {
              _tmpEndLine = _cursor.getInt(_cursorIndexOfEndLine);
            }
            final String _tmpTranslationText;
            if (_cursor.isNull(_cursorIndexOfTranslationText)) {
              _tmpTranslationText = null;
            } else {
              _tmpTranslationText = _cursor.getString(_cursorIndexOfTranslationText);
            }
            final String _tmpTranslator;
            if (_cursor.isNull(_cursorIndexOfTranslator)) {
              _tmpTranslator = null;
            } else {
              _tmpTranslator = _cursor.getString(_cursorIndexOfTranslator);
            }
            _item = new TranslationSegmentEntity(_tmpId,_tmpBookId,_tmpStartLine,_tmpEndLine,_tmpTranslationText,_tmpTranslator);
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

  @Override
  public Object hasTranslationsForWork(final String workId,
      final Continuation<? super Boolean> $completion) {
    final String _sql = "\n"
            + "        SELECT EXISTS(\n"
            + "            SELECT 1 FROM translation_segments ts \n"
            + "            JOIN books b ON ts.book_id = b.id \n"
            + "            WHERE b.work_id = ?\n"
            + "        )\n"
            + "    ";
    final RoomSQLiteQuery _statement = RoomSQLiteQuery.acquire(_sql, 1);
    int _argIndex = 1;
    if (workId == null) {
      _statement.bindNull(_argIndex);
    } else {
      _statement.bindString(_argIndex, workId);
    }
    final CancellationSignal _cancellationSignal = DBUtil.createCancellationSignal();
    return CoroutinesRoom.execute(__db, false, _cancellationSignal, new Callable<Boolean>() {
      @Override
      @NonNull
      public Boolean call() throws Exception {
        final Cursor _cursor = DBUtil.query(__db, _statement, false, null);
        try {
          final Boolean _result;
          if (_cursor.moveToFirst()) {
            final Integer _tmp;
            if (_cursor.isNull(0)) {
              _tmp = null;
            } else {
              _tmp = _cursor.getInt(0);
            }
            _result = _tmp == null ? null : _tmp != 0;
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

  @NonNull
  public static List<Class<?>> getRequiredConverters() {
    return Collections.emptyList();
  }
}

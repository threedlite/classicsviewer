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
import com.classicsviewer.app.database.entities.TextLineEntity;
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
public final class TextLineDao_Impl implements TextLineDao {
  private final RoomDatabase __db;

  public TextLineDao_Impl(@NonNull final RoomDatabase __db) {
    this.__db = __db;
  }

  @Override
  public Object getByBook(final String bookId,
      final Continuation<? super List<TextLineEntity>> $completion) {
    final String _sql = "SELECT * FROM text_lines WHERE book_id = ? ORDER BY line_number";
    final RoomSQLiteQuery _statement = RoomSQLiteQuery.acquire(_sql, 1);
    int _argIndex = 1;
    if (bookId == null) {
      _statement.bindNull(_argIndex);
    } else {
      _statement.bindString(_argIndex, bookId);
    }
    final CancellationSignal _cancellationSignal = DBUtil.createCancellationSignal();
    return CoroutinesRoom.execute(__db, false, _cancellationSignal, new Callable<List<TextLineEntity>>() {
      @Override
      @NonNull
      public List<TextLineEntity> call() throws Exception {
        final Cursor _cursor = DBUtil.query(__db, _statement, false, null);
        try {
          final int _cursorIndexOfId = CursorUtil.getColumnIndexOrThrow(_cursor, "id");
          final int _cursorIndexOfBookId = CursorUtil.getColumnIndexOrThrow(_cursor, "book_id");
          final int _cursorIndexOfLineNumber = CursorUtil.getColumnIndexOrThrow(_cursor, "line_number");
          final int _cursorIndexOfLineText = CursorUtil.getColumnIndexOrThrow(_cursor, "line_text");
          final int _cursorIndexOfLineXml = CursorUtil.getColumnIndexOrThrow(_cursor, "line_xml");
          final int _cursorIndexOfSpeaker = CursorUtil.getColumnIndexOrThrow(_cursor, "speaker");
          final List<TextLineEntity> _result = new ArrayList<TextLineEntity>(_cursor.getCount());
          while (_cursor.moveToNext()) {
            final TextLineEntity _item;
            final long _tmpId;
            _tmpId = _cursor.getLong(_cursorIndexOfId);
            final String _tmpBookId;
            if (_cursor.isNull(_cursorIndexOfBookId)) {
              _tmpBookId = null;
            } else {
              _tmpBookId = _cursor.getString(_cursorIndexOfBookId);
            }
            final int _tmpLineNumber;
            _tmpLineNumber = _cursor.getInt(_cursorIndexOfLineNumber);
            final String _tmpLineText;
            if (_cursor.isNull(_cursorIndexOfLineText)) {
              _tmpLineText = null;
            } else {
              _tmpLineText = _cursor.getString(_cursorIndexOfLineText);
            }
            final String _tmpLineXml;
            if (_cursor.isNull(_cursorIndexOfLineXml)) {
              _tmpLineXml = null;
            } else {
              _tmpLineXml = _cursor.getString(_cursorIndexOfLineXml);
            }
            final String _tmpSpeaker;
            if (_cursor.isNull(_cursorIndexOfSpeaker)) {
              _tmpSpeaker = null;
            } else {
              _tmpSpeaker = _cursor.getString(_cursorIndexOfSpeaker);
            }
            _item = new TextLineEntity(_tmpId,_tmpBookId,_tmpLineNumber,_tmpLineText,_tmpLineXml,_tmpSpeaker);
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
  public Object getByBookAndRange(final String bookId, final int startLine, final int endLine,
      final Continuation<? super List<TextLineEntity>> $completion) {
    final String _sql = "SELECT * FROM text_lines WHERE book_id = ? AND line_number >= ? AND line_number <= ? ORDER BY line_number";
    final RoomSQLiteQuery _statement = RoomSQLiteQuery.acquire(_sql, 3);
    int _argIndex = 1;
    if (bookId == null) {
      _statement.bindNull(_argIndex);
    } else {
      _statement.bindString(_argIndex, bookId);
    }
    _argIndex = 2;
    _statement.bindLong(_argIndex, startLine);
    _argIndex = 3;
    _statement.bindLong(_argIndex, endLine);
    final CancellationSignal _cancellationSignal = DBUtil.createCancellationSignal();
    return CoroutinesRoom.execute(__db, false, _cancellationSignal, new Callable<List<TextLineEntity>>() {
      @Override
      @NonNull
      public List<TextLineEntity> call() throws Exception {
        final Cursor _cursor = DBUtil.query(__db, _statement, false, null);
        try {
          final int _cursorIndexOfId = CursorUtil.getColumnIndexOrThrow(_cursor, "id");
          final int _cursorIndexOfBookId = CursorUtil.getColumnIndexOrThrow(_cursor, "book_id");
          final int _cursorIndexOfLineNumber = CursorUtil.getColumnIndexOrThrow(_cursor, "line_number");
          final int _cursorIndexOfLineText = CursorUtil.getColumnIndexOrThrow(_cursor, "line_text");
          final int _cursorIndexOfLineXml = CursorUtil.getColumnIndexOrThrow(_cursor, "line_xml");
          final int _cursorIndexOfSpeaker = CursorUtil.getColumnIndexOrThrow(_cursor, "speaker");
          final List<TextLineEntity> _result = new ArrayList<TextLineEntity>(_cursor.getCount());
          while (_cursor.moveToNext()) {
            final TextLineEntity _item;
            final long _tmpId;
            _tmpId = _cursor.getLong(_cursorIndexOfId);
            final String _tmpBookId;
            if (_cursor.isNull(_cursorIndexOfBookId)) {
              _tmpBookId = null;
            } else {
              _tmpBookId = _cursor.getString(_cursorIndexOfBookId);
            }
            final int _tmpLineNumber;
            _tmpLineNumber = _cursor.getInt(_cursorIndexOfLineNumber);
            final String _tmpLineText;
            if (_cursor.isNull(_cursorIndexOfLineText)) {
              _tmpLineText = null;
            } else {
              _tmpLineText = _cursor.getString(_cursorIndexOfLineText);
            }
            final String _tmpLineXml;
            if (_cursor.isNull(_cursorIndexOfLineXml)) {
              _tmpLineXml = null;
            } else {
              _tmpLineXml = _cursor.getString(_cursorIndexOfLineXml);
            }
            final String _tmpSpeaker;
            if (_cursor.isNull(_cursorIndexOfSpeaker)) {
              _tmpSpeaker = null;
            } else {
              _tmpSpeaker = _cursor.getString(_cursorIndexOfSpeaker);
            }
            _item = new TextLineEntity(_tmpId,_tmpBookId,_tmpLineNumber,_tmpLineText,_tmpLineXml,_tmpSpeaker);
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
  public Object getLineCountByBook(final String bookId,
      final Continuation<? super Integer> $completion) {
    final String _sql = "SELECT COUNT(*) FROM text_lines WHERE book_id = ?";
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
  public Object getFirstLineNumber(final String bookId,
      final Continuation<? super Integer> $completion) {
    final String _sql = "SELECT MIN(line_number) FROM text_lines WHERE book_id = ?";
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
      @Nullable
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
  public Object getLastLineNumber(final String bookId,
      final Continuation<? super Integer> $completion) {
    final String _sql = "SELECT MAX(line_number) FROM text_lines WHERE book_id = ?";
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
      @Nullable
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

  @NonNull
  public static List<Class<?>> getRequiredConverters() {
    return Collections.emptyList();
  }
}

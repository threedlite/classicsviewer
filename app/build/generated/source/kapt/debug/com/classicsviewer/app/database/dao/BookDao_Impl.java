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
import com.classicsviewer.app.database.entities.BookEntity;
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
public final class BookDao_Impl implements BookDao {
  private final RoomDatabase __db;

  public BookDao_Impl(@NonNull final RoomDatabase __db) {
    this.__db = __db;
  }

  @Override
  public Object getByWork(final String workId,
      final Continuation<? super List<BookEntity>> $completion) {
    final String _sql = "SELECT * FROM books WHERE work_id = ? ORDER BY book_number";
    final RoomSQLiteQuery _statement = RoomSQLiteQuery.acquire(_sql, 1);
    int _argIndex = 1;
    if (workId == null) {
      _statement.bindNull(_argIndex);
    } else {
      _statement.bindString(_argIndex, workId);
    }
    final CancellationSignal _cancellationSignal = DBUtil.createCancellationSignal();
    return CoroutinesRoom.execute(__db, false, _cancellationSignal, new Callable<List<BookEntity>>() {
      @Override
      @NonNull
      public List<BookEntity> call() throws Exception {
        final Cursor _cursor = DBUtil.query(__db, _statement, false, null);
        try {
          final int _cursorIndexOfId = CursorUtil.getColumnIndexOrThrow(_cursor, "id");
          final int _cursorIndexOfWorkId = CursorUtil.getColumnIndexOrThrow(_cursor, "work_id");
          final int _cursorIndexOfBookNumber = CursorUtil.getColumnIndexOrThrow(_cursor, "book_number");
          final int _cursorIndexOfLabel = CursorUtil.getColumnIndexOrThrow(_cursor, "label");
          final int _cursorIndexOfStartLine = CursorUtil.getColumnIndexOrThrow(_cursor, "start_line");
          final int _cursorIndexOfEndLine = CursorUtil.getColumnIndexOrThrow(_cursor, "end_line");
          final int _cursorIndexOfLineCount = CursorUtil.getColumnIndexOrThrow(_cursor, "line_count");
          final List<BookEntity> _result = new ArrayList<BookEntity>(_cursor.getCount());
          while (_cursor.moveToNext()) {
            final BookEntity _item;
            final String _tmpId;
            if (_cursor.isNull(_cursorIndexOfId)) {
              _tmpId = null;
            } else {
              _tmpId = _cursor.getString(_cursorIndexOfId);
            }
            final String _tmpWorkId;
            if (_cursor.isNull(_cursorIndexOfWorkId)) {
              _tmpWorkId = null;
            } else {
              _tmpWorkId = _cursor.getString(_cursorIndexOfWorkId);
            }
            final int _tmpBookNumber;
            _tmpBookNumber = _cursor.getInt(_cursorIndexOfBookNumber);
            final String _tmpLabel;
            if (_cursor.isNull(_cursorIndexOfLabel)) {
              _tmpLabel = null;
            } else {
              _tmpLabel = _cursor.getString(_cursorIndexOfLabel);
            }
            final Integer _tmpStartLine;
            if (_cursor.isNull(_cursorIndexOfStartLine)) {
              _tmpStartLine = null;
            } else {
              _tmpStartLine = _cursor.getInt(_cursorIndexOfStartLine);
            }
            final Integer _tmpEndLine;
            if (_cursor.isNull(_cursorIndexOfEndLine)) {
              _tmpEndLine = null;
            } else {
              _tmpEndLine = _cursor.getInt(_cursorIndexOfEndLine);
            }
            final Integer _tmpLineCount;
            if (_cursor.isNull(_cursorIndexOfLineCount)) {
              _tmpLineCount = null;
            } else {
              _tmpLineCount = _cursor.getInt(_cursorIndexOfLineCount);
            }
            _item = new BookEntity(_tmpId,_tmpWorkId,_tmpBookNumber,_tmpLabel,_tmpStartLine,_tmpEndLine,_tmpLineCount);
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
  public Object getById(final String bookId, final Continuation<? super BookEntity> $completion) {
    final String _sql = "SELECT * FROM books WHERE id = ?";
    final RoomSQLiteQuery _statement = RoomSQLiteQuery.acquire(_sql, 1);
    int _argIndex = 1;
    if (bookId == null) {
      _statement.bindNull(_argIndex);
    } else {
      _statement.bindString(_argIndex, bookId);
    }
    final CancellationSignal _cancellationSignal = DBUtil.createCancellationSignal();
    return CoroutinesRoom.execute(__db, false, _cancellationSignal, new Callable<BookEntity>() {
      @Override
      @Nullable
      public BookEntity call() throws Exception {
        final Cursor _cursor = DBUtil.query(__db, _statement, false, null);
        try {
          final int _cursorIndexOfId = CursorUtil.getColumnIndexOrThrow(_cursor, "id");
          final int _cursorIndexOfWorkId = CursorUtil.getColumnIndexOrThrow(_cursor, "work_id");
          final int _cursorIndexOfBookNumber = CursorUtil.getColumnIndexOrThrow(_cursor, "book_number");
          final int _cursorIndexOfLabel = CursorUtil.getColumnIndexOrThrow(_cursor, "label");
          final int _cursorIndexOfStartLine = CursorUtil.getColumnIndexOrThrow(_cursor, "start_line");
          final int _cursorIndexOfEndLine = CursorUtil.getColumnIndexOrThrow(_cursor, "end_line");
          final int _cursorIndexOfLineCount = CursorUtil.getColumnIndexOrThrow(_cursor, "line_count");
          final BookEntity _result;
          if (_cursor.moveToFirst()) {
            final String _tmpId;
            if (_cursor.isNull(_cursorIndexOfId)) {
              _tmpId = null;
            } else {
              _tmpId = _cursor.getString(_cursorIndexOfId);
            }
            final String _tmpWorkId;
            if (_cursor.isNull(_cursorIndexOfWorkId)) {
              _tmpWorkId = null;
            } else {
              _tmpWorkId = _cursor.getString(_cursorIndexOfWorkId);
            }
            final int _tmpBookNumber;
            _tmpBookNumber = _cursor.getInt(_cursorIndexOfBookNumber);
            final String _tmpLabel;
            if (_cursor.isNull(_cursorIndexOfLabel)) {
              _tmpLabel = null;
            } else {
              _tmpLabel = _cursor.getString(_cursorIndexOfLabel);
            }
            final Integer _tmpStartLine;
            if (_cursor.isNull(_cursorIndexOfStartLine)) {
              _tmpStartLine = null;
            } else {
              _tmpStartLine = _cursor.getInt(_cursorIndexOfStartLine);
            }
            final Integer _tmpEndLine;
            if (_cursor.isNull(_cursorIndexOfEndLine)) {
              _tmpEndLine = null;
            } else {
              _tmpEndLine = _cursor.getInt(_cursorIndexOfEndLine);
            }
            final Integer _tmpLineCount;
            if (_cursor.isNull(_cursorIndexOfLineCount)) {
              _tmpLineCount = null;
            } else {
              _tmpLineCount = _cursor.getInt(_cursorIndexOfLineCount);
            }
            _result = new BookEntity(_tmpId,_tmpWorkId,_tmpBookNumber,_tmpLabel,_tmpStartLine,_tmpEndLine,_tmpLineCount);
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
  public Object getBookCountByWork(final String workId,
      final Continuation<? super Integer> $completion) {
    final String _sql = "SELECT COUNT(*) FROM books WHERE work_id = ?";
    final RoomSQLiteQuery _statement = RoomSQLiteQuery.acquire(_sql, 1);
    int _argIndex = 1;
    if (workId == null) {
      _statement.bindNull(_argIndex);
    } else {
      _statement.bindString(_argIndex, workId);
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

  @NonNull
  public static List<Class<?>> getRequiredConverters() {
    return Collections.emptyList();
  }
}

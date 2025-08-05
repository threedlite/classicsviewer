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
import com.classicsviewer.app.database.entities.WorkEntity;
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
public final class WorkDao_Impl implements WorkDao {
  private final RoomDatabase __db;

  public WorkDao_Impl(@NonNull final RoomDatabase __db) {
    this.__db = __db;
  }

  @Override
  public Object getByAuthor(final String authorId,
      final Continuation<? super List<WorkEntity>> $completion) {
    final String _sql = "SELECT * FROM works WHERE author_id = ? ORDER BY title";
    final RoomSQLiteQuery _statement = RoomSQLiteQuery.acquire(_sql, 1);
    int _argIndex = 1;
    if (authorId == null) {
      _statement.bindNull(_argIndex);
    } else {
      _statement.bindString(_argIndex, authorId);
    }
    final CancellationSignal _cancellationSignal = DBUtil.createCancellationSignal();
    return CoroutinesRoom.execute(__db, false, _cancellationSignal, new Callable<List<WorkEntity>>() {
      @Override
      @NonNull
      public List<WorkEntity> call() throws Exception {
        final Cursor _cursor = DBUtil.query(__db, _statement, false, null);
        try {
          final int _cursorIndexOfId = CursorUtil.getColumnIndexOrThrow(_cursor, "id");
          final int _cursorIndexOfAuthorId = CursorUtil.getColumnIndexOrThrow(_cursor, "author_id");
          final int _cursorIndexOfTitle = CursorUtil.getColumnIndexOrThrow(_cursor, "title");
          final int _cursorIndexOfTitleAlt = CursorUtil.getColumnIndexOrThrow(_cursor, "title_alt");
          final int _cursorIndexOfTitleEnglish = CursorUtil.getColumnIndexOrThrow(_cursor, "title_english");
          final int _cursorIndexOfType = CursorUtil.getColumnIndexOrThrow(_cursor, "type");
          final int _cursorIndexOfUrn = CursorUtil.getColumnIndexOrThrow(_cursor, "urn");
          final int _cursorIndexOfDescription = CursorUtil.getColumnIndexOrThrow(_cursor, "description");
          final List<WorkEntity> _result = new ArrayList<WorkEntity>(_cursor.getCount());
          while (_cursor.moveToNext()) {
            final WorkEntity _item;
            final String _tmpId;
            if (_cursor.isNull(_cursorIndexOfId)) {
              _tmpId = null;
            } else {
              _tmpId = _cursor.getString(_cursorIndexOfId);
            }
            final String _tmpAuthorId;
            if (_cursor.isNull(_cursorIndexOfAuthorId)) {
              _tmpAuthorId = null;
            } else {
              _tmpAuthorId = _cursor.getString(_cursorIndexOfAuthorId);
            }
            final String _tmpTitle;
            if (_cursor.isNull(_cursorIndexOfTitle)) {
              _tmpTitle = null;
            } else {
              _tmpTitle = _cursor.getString(_cursorIndexOfTitle);
            }
            final String _tmpTitleAlt;
            if (_cursor.isNull(_cursorIndexOfTitleAlt)) {
              _tmpTitleAlt = null;
            } else {
              _tmpTitleAlt = _cursor.getString(_cursorIndexOfTitleAlt);
            }
            final String _tmpTitleEnglish;
            if (_cursor.isNull(_cursorIndexOfTitleEnglish)) {
              _tmpTitleEnglish = null;
            } else {
              _tmpTitleEnglish = _cursor.getString(_cursorIndexOfTitleEnglish);
            }
            final String _tmpType;
            if (_cursor.isNull(_cursorIndexOfType)) {
              _tmpType = null;
            } else {
              _tmpType = _cursor.getString(_cursorIndexOfType);
            }
            final String _tmpUrn;
            if (_cursor.isNull(_cursorIndexOfUrn)) {
              _tmpUrn = null;
            } else {
              _tmpUrn = _cursor.getString(_cursorIndexOfUrn);
            }
            final String _tmpDescription;
            if (_cursor.isNull(_cursorIndexOfDescription)) {
              _tmpDescription = null;
            } else {
              _tmpDescription = _cursor.getString(_cursorIndexOfDescription);
            }
            _item = new WorkEntity(_tmpId,_tmpAuthorId,_tmpTitle,_tmpTitleAlt,_tmpTitleEnglish,_tmpType,_tmpUrn,_tmpDescription);
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
  public Object getById(final String workId, final Continuation<? super WorkEntity> $completion) {
    final String _sql = "SELECT * FROM works WHERE id = ?";
    final RoomSQLiteQuery _statement = RoomSQLiteQuery.acquire(_sql, 1);
    int _argIndex = 1;
    if (workId == null) {
      _statement.bindNull(_argIndex);
    } else {
      _statement.bindString(_argIndex, workId);
    }
    final CancellationSignal _cancellationSignal = DBUtil.createCancellationSignal();
    return CoroutinesRoom.execute(__db, false, _cancellationSignal, new Callable<WorkEntity>() {
      @Override
      @Nullable
      public WorkEntity call() throws Exception {
        final Cursor _cursor = DBUtil.query(__db, _statement, false, null);
        try {
          final int _cursorIndexOfId = CursorUtil.getColumnIndexOrThrow(_cursor, "id");
          final int _cursorIndexOfAuthorId = CursorUtil.getColumnIndexOrThrow(_cursor, "author_id");
          final int _cursorIndexOfTitle = CursorUtil.getColumnIndexOrThrow(_cursor, "title");
          final int _cursorIndexOfTitleAlt = CursorUtil.getColumnIndexOrThrow(_cursor, "title_alt");
          final int _cursorIndexOfTitleEnglish = CursorUtil.getColumnIndexOrThrow(_cursor, "title_english");
          final int _cursorIndexOfType = CursorUtil.getColumnIndexOrThrow(_cursor, "type");
          final int _cursorIndexOfUrn = CursorUtil.getColumnIndexOrThrow(_cursor, "urn");
          final int _cursorIndexOfDescription = CursorUtil.getColumnIndexOrThrow(_cursor, "description");
          final WorkEntity _result;
          if (_cursor.moveToFirst()) {
            final String _tmpId;
            if (_cursor.isNull(_cursorIndexOfId)) {
              _tmpId = null;
            } else {
              _tmpId = _cursor.getString(_cursorIndexOfId);
            }
            final String _tmpAuthorId;
            if (_cursor.isNull(_cursorIndexOfAuthorId)) {
              _tmpAuthorId = null;
            } else {
              _tmpAuthorId = _cursor.getString(_cursorIndexOfAuthorId);
            }
            final String _tmpTitle;
            if (_cursor.isNull(_cursorIndexOfTitle)) {
              _tmpTitle = null;
            } else {
              _tmpTitle = _cursor.getString(_cursorIndexOfTitle);
            }
            final String _tmpTitleAlt;
            if (_cursor.isNull(_cursorIndexOfTitleAlt)) {
              _tmpTitleAlt = null;
            } else {
              _tmpTitleAlt = _cursor.getString(_cursorIndexOfTitleAlt);
            }
            final String _tmpTitleEnglish;
            if (_cursor.isNull(_cursorIndexOfTitleEnglish)) {
              _tmpTitleEnglish = null;
            } else {
              _tmpTitleEnglish = _cursor.getString(_cursorIndexOfTitleEnglish);
            }
            final String _tmpType;
            if (_cursor.isNull(_cursorIndexOfType)) {
              _tmpType = null;
            } else {
              _tmpType = _cursor.getString(_cursorIndexOfType);
            }
            final String _tmpUrn;
            if (_cursor.isNull(_cursorIndexOfUrn)) {
              _tmpUrn = null;
            } else {
              _tmpUrn = _cursor.getString(_cursorIndexOfUrn);
            }
            final String _tmpDescription;
            if (_cursor.isNull(_cursorIndexOfDescription)) {
              _tmpDescription = null;
            } else {
              _tmpDescription = _cursor.getString(_cursorIndexOfDescription);
            }
            _result = new WorkEntity(_tmpId,_tmpAuthorId,_tmpTitle,_tmpTitleAlt,_tmpTitleEnglish,_tmpType,_tmpUrn,_tmpDescription);
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
  public Object getWorkCountByAuthor(final String authorId,
      final Continuation<? super Integer> $completion) {
    final String _sql = "SELECT COUNT(*) FROM works WHERE author_id = ?";
    final RoomSQLiteQuery _statement = RoomSQLiteQuery.acquire(_sql, 1);
    int _argIndex = 1;
    if (authorId == null) {
      _statement.bindNull(_argIndex);
    } else {
      _statement.bindString(_argIndex, authorId);
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

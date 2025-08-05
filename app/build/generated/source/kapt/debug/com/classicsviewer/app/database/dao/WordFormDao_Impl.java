package com.classicsviewer.app.database.dao;

import android.database.Cursor;
import android.os.CancellationSignal;
import androidx.annotation.NonNull;
import androidx.room.CoroutinesRoom;
import androidx.room.RoomDatabase;
import androidx.room.RoomSQLiteQuery;
import androidx.room.util.CursorUtil;
import androidx.room.util.DBUtil;
import com.classicsviewer.app.database.entities.WordFormEntity;
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
public final class WordFormDao_Impl implements WordFormDao {
  private final RoomDatabase __db;

  public WordFormDao_Impl(@NonNull final RoomDatabase __db) {
    this.__db = __db;
  }

  @Override
  public Object getByBookAndLine(final String bookId, final int lineNumber,
      final Continuation<? super List<WordFormEntity>> $completion) {
    final String _sql = "SELECT * FROM word_forms WHERE book_id = ? AND line_number = ? ORDER BY word_position";
    final RoomSQLiteQuery _statement = RoomSQLiteQuery.acquire(_sql, 2);
    int _argIndex = 1;
    if (bookId == null) {
      _statement.bindNull(_argIndex);
    } else {
      _statement.bindString(_argIndex, bookId);
    }
    _argIndex = 2;
    _statement.bindLong(_argIndex, lineNumber);
    final CancellationSignal _cancellationSignal = DBUtil.createCancellationSignal();
    return CoroutinesRoom.execute(__db, false, _cancellationSignal, new Callable<List<WordFormEntity>>() {
      @Override
      @NonNull
      public List<WordFormEntity> call() throws Exception {
        final Cursor _cursor = DBUtil.query(__db, _statement, false, null);
        try {
          final int _cursorIndexOfWord = CursorUtil.getColumnIndexOrThrow(_cursor, "word");
          final int _cursorIndexOfWordNormalized = CursorUtil.getColumnIndexOrThrow(_cursor, "word_normalized");
          final int _cursorIndexOfBookId = CursorUtil.getColumnIndexOrThrow(_cursor, "book_id");
          final int _cursorIndexOfLineNumber = CursorUtil.getColumnIndexOrThrow(_cursor, "line_number");
          final int _cursorIndexOfWordPosition = CursorUtil.getColumnIndexOrThrow(_cursor, "word_position");
          final int _cursorIndexOfCharStart = CursorUtil.getColumnIndexOrThrow(_cursor, "char_start");
          final int _cursorIndexOfCharEnd = CursorUtil.getColumnIndexOrThrow(_cursor, "char_end");
          final List<WordFormEntity> _result = new ArrayList<WordFormEntity>(_cursor.getCount());
          while (_cursor.moveToNext()) {
            final WordFormEntity _item;
            final String _tmpWord;
            if (_cursor.isNull(_cursorIndexOfWord)) {
              _tmpWord = null;
            } else {
              _tmpWord = _cursor.getString(_cursorIndexOfWord);
            }
            final String _tmpWordNormalized;
            if (_cursor.isNull(_cursorIndexOfWordNormalized)) {
              _tmpWordNormalized = null;
            } else {
              _tmpWordNormalized = _cursor.getString(_cursorIndexOfWordNormalized);
            }
            final String _tmpBookId;
            if (_cursor.isNull(_cursorIndexOfBookId)) {
              _tmpBookId = null;
            } else {
              _tmpBookId = _cursor.getString(_cursorIndexOfBookId);
            }
            final int _tmpLineNumber;
            _tmpLineNumber = _cursor.getInt(_cursorIndexOfLineNumber);
            final int _tmpWordPosition;
            _tmpWordPosition = _cursor.getInt(_cursorIndexOfWordPosition);
            final int _tmpCharStart;
            _tmpCharStart = _cursor.getInt(_cursorIndexOfCharStart);
            final int _tmpCharEnd;
            _tmpCharEnd = _cursor.getInt(_cursorIndexOfCharEnd);
            _item = new WordFormEntity(_tmpWord,_tmpWordNormalized,_tmpBookId,_tmpLineNumber,_tmpWordPosition,_tmpCharStart,_tmpCharEnd);
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
  public Object findOccurrences(final String normalizedForm,
      final Continuation<? super List<OccurrenceResult>> $completion) {
    final String _sql = "\n"
            + "        SELECT \n"
            + "            wf.book_id as bookId,\n"
            + "            wf.line_number as lineNumber,\n"
            + "            tl.line_text as lineText,\n"
            + "            wf.word_position as position\n"
            + "        FROM word_forms wf\n"
            + "        JOIN text_lines tl ON wf.book_id = tl.book_id AND wf.line_number = tl.line_number\n"
            + "        WHERE wf.word_normalized = ?\n"
            + "        ORDER BY wf.book_id, wf.line_number, wf.word_position\n"
            + "        LIMIT 500\n"
            + "    ";
    final RoomSQLiteQuery _statement = RoomSQLiteQuery.acquire(_sql, 1);
    int _argIndex = 1;
    if (normalizedForm == null) {
      _statement.bindNull(_argIndex);
    } else {
      _statement.bindString(_argIndex, normalizedForm);
    }
    final CancellationSignal _cancellationSignal = DBUtil.createCancellationSignal();
    return CoroutinesRoom.execute(__db, false, _cancellationSignal, new Callable<List<OccurrenceResult>>() {
      @Override
      @NonNull
      public List<OccurrenceResult> call() throws Exception {
        final Cursor _cursor = DBUtil.query(__db, _statement, false, null);
        try {
          final int _cursorIndexOfBookId = 0;
          final int _cursorIndexOfLineNumber = 1;
          final int _cursorIndexOfLineText = 2;
          final int _cursorIndexOfPosition = 3;
          final List<OccurrenceResult> _result = new ArrayList<OccurrenceResult>(_cursor.getCount());
          while (_cursor.moveToNext()) {
            final OccurrenceResult _item;
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
            final int _tmpPosition;
            _tmpPosition = _cursor.getInt(_cursorIndexOfPosition);
            _item = new OccurrenceResult(_tmpBookId,_tmpLineNumber,_tmpLineText,_tmpPosition);
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
  public Object getUniqueWordCount(final Continuation<? super Integer> $completion) {
    final String _sql = "SELECT COUNT(DISTINCT word_normalized) FROM word_forms";
    final RoomSQLiteQuery _statement = RoomSQLiteQuery.acquire(_sql, 0);
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
  public Object countOccurrences(final String normalizedForm,
      final Continuation<? super Integer> $completion) {
    final String _sql = "SELECT COUNT(*) FROM word_forms WHERE word_normalized = ?";
    final RoomSQLiteQuery _statement = RoomSQLiteQuery.acquire(_sql, 1);
    int _argIndex = 1;
    if (normalizedForm == null) {
      _statement.bindNull(_argIndex);
    } else {
      _statement.bindString(_argIndex, normalizedForm);
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

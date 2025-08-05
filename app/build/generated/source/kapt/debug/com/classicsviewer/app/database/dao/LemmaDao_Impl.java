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
import com.classicsviewer.app.database.entities.LemmaMapEntity;
import java.lang.Class;
import java.lang.Double;
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
public final class LemmaDao_Impl implements LemmaDao {
  private final RoomDatabase __db;

  public LemmaDao_Impl(@NonNull final RoomDatabase __db) {
    this.__db = __db;
  }

  @Override
  public Object getLemmasForForm(final String normalizedForm,
      final Continuation<? super List<LemmaMapEntity>> $completion) {
    final String _sql = "SELECT * FROM lemma_map WHERE word_normalized = ?";
    final RoomSQLiteQuery _statement = RoomSQLiteQuery.acquire(_sql, 1);
    int _argIndex = 1;
    if (normalizedForm == null) {
      _statement.bindNull(_argIndex);
    } else {
      _statement.bindString(_argIndex, normalizedForm);
    }
    final CancellationSignal _cancellationSignal = DBUtil.createCancellationSignal();
    return CoroutinesRoom.execute(__db, false, _cancellationSignal, new Callable<List<LemmaMapEntity>>() {
      @Override
      @NonNull
      public List<LemmaMapEntity> call() throws Exception {
        final Cursor _cursor = DBUtil.query(__db, _statement, false, null);
        try {
          final int _cursorIndexOfWordForm = CursorUtil.getColumnIndexOrThrow(_cursor, "word_form");
          final int _cursorIndexOfWordNormalized = CursorUtil.getColumnIndexOrThrow(_cursor, "word_normalized");
          final int _cursorIndexOfLemma = CursorUtil.getColumnIndexOrThrow(_cursor, "lemma");
          final int _cursorIndexOfConfidence = CursorUtil.getColumnIndexOrThrow(_cursor, "confidence");
          final int _cursorIndexOfSource = CursorUtil.getColumnIndexOrThrow(_cursor, "source");
          final int _cursorIndexOfMorphInfo = CursorUtil.getColumnIndexOrThrow(_cursor, "morph_info");
          final List<LemmaMapEntity> _result = new ArrayList<LemmaMapEntity>(_cursor.getCount());
          while (_cursor.moveToNext()) {
            final LemmaMapEntity _item;
            final String _tmpWordForm;
            if (_cursor.isNull(_cursorIndexOfWordForm)) {
              _tmpWordForm = null;
            } else {
              _tmpWordForm = _cursor.getString(_cursorIndexOfWordForm);
            }
            final String _tmpWordNormalized;
            if (_cursor.isNull(_cursorIndexOfWordNormalized)) {
              _tmpWordNormalized = null;
            } else {
              _tmpWordNormalized = _cursor.getString(_cursorIndexOfWordNormalized);
            }
            final String _tmpLemma;
            if (_cursor.isNull(_cursorIndexOfLemma)) {
              _tmpLemma = null;
            } else {
              _tmpLemma = _cursor.getString(_cursorIndexOfLemma);
            }
            final Double _tmpConfidence;
            if (_cursor.isNull(_cursorIndexOfConfidence)) {
              _tmpConfidence = null;
            } else {
              _tmpConfidence = _cursor.getDouble(_cursorIndexOfConfidence);
            }
            final String _tmpSource;
            if (_cursor.isNull(_cursorIndexOfSource)) {
              _tmpSource = null;
            } else {
              _tmpSource = _cursor.getString(_cursorIndexOfSource);
            }
            final String _tmpMorphInfo;
            if (_cursor.isNull(_cursorIndexOfMorphInfo)) {
              _tmpMorphInfo = null;
            } else {
              _tmpMorphInfo = _cursor.getString(_cursorIndexOfMorphInfo);
            }
            _item = new LemmaMapEntity(_tmpWordForm,_tmpWordNormalized,_tmpLemma,_tmpConfidence,_tmpSource,_tmpMorphInfo);
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
  public Object getLemmaCandidates(final String normalizedForm,
      final Continuation<? super List<String>> $completion) {
    final String _sql = "SELECT DISTINCT lemma FROM lemma_map WHERE word_normalized = ?";
    final RoomSQLiteQuery _statement = RoomSQLiteQuery.acquire(_sql, 1);
    int _argIndex = 1;
    if (normalizedForm == null) {
      _statement.bindNull(_argIndex);
    } else {
      _statement.bindString(_argIndex, normalizedForm);
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
  public Object getUniqueLemmaCount(final Continuation<? super Integer> $completion) {
    final String _sql = "SELECT COUNT(DISTINCT lemma) FROM lemma_map";
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
  public Object getLemmaMapping(final String normalizedForm,
      final Continuation<? super LemmaMapEntity> $completion) {
    final String _sql = "SELECT * FROM lemma_map WHERE word_normalized = ? ORDER BY confidence DESC LIMIT 1";
    final RoomSQLiteQuery _statement = RoomSQLiteQuery.acquire(_sql, 1);
    int _argIndex = 1;
    if (normalizedForm == null) {
      _statement.bindNull(_argIndex);
    } else {
      _statement.bindString(_argIndex, normalizedForm);
    }
    final CancellationSignal _cancellationSignal = DBUtil.createCancellationSignal();
    return CoroutinesRoom.execute(__db, false, _cancellationSignal, new Callable<LemmaMapEntity>() {
      @Override
      @Nullable
      public LemmaMapEntity call() throws Exception {
        final Cursor _cursor = DBUtil.query(__db, _statement, false, null);
        try {
          final int _cursorIndexOfWordForm = CursorUtil.getColumnIndexOrThrow(_cursor, "word_form");
          final int _cursorIndexOfWordNormalized = CursorUtil.getColumnIndexOrThrow(_cursor, "word_normalized");
          final int _cursorIndexOfLemma = CursorUtil.getColumnIndexOrThrow(_cursor, "lemma");
          final int _cursorIndexOfConfidence = CursorUtil.getColumnIndexOrThrow(_cursor, "confidence");
          final int _cursorIndexOfSource = CursorUtil.getColumnIndexOrThrow(_cursor, "source");
          final int _cursorIndexOfMorphInfo = CursorUtil.getColumnIndexOrThrow(_cursor, "morph_info");
          final LemmaMapEntity _result;
          if (_cursor.moveToFirst()) {
            final String _tmpWordForm;
            if (_cursor.isNull(_cursorIndexOfWordForm)) {
              _tmpWordForm = null;
            } else {
              _tmpWordForm = _cursor.getString(_cursorIndexOfWordForm);
            }
            final String _tmpWordNormalized;
            if (_cursor.isNull(_cursorIndexOfWordNormalized)) {
              _tmpWordNormalized = null;
            } else {
              _tmpWordNormalized = _cursor.getString(_cursorIndexOfWordNormalized);
            }
            final String _tmpLemma;
            if (_cursor.isNull(_cursorIndexOfLemma)) {
              _tmpLemma = null;
            } else {
              _tmpLemma = _cursor.getString(_cursorIndexOfLemma);
            }
            final Double _tmpConfidence;
            if (_cursor.isNull(_cursorIndexOfConfidence)) {
              _tmpConfidence = null;
            } else {
              _tmpConfidence = _cursor.getDouble(_cursorIndexOfConfidence);
            }
            final String _tmpSource;
            if (_cursor.isNull(_cursorIndexOfSource)) {
              _tmpSource = null;
            } else {
              _tmpSource = _cursor.getString(_cursorIndexOfSource);
            }
            final String _tmpMorphInfo;
            if (_cursor.isNull(_cursorIndexOfMorphInfo)) {
              _tmpMorphInfo = null;
            } else {
              _tmpMorphInfo = _cursor.getString(_cursorIndexOfMorphInfo);
            }
            _result = new LemmaMapEntity(_tmpWordForm,_tmpWordNormalized,_tmpLemma,_tmpConfidence,_tmpSource,_tmpMorphInfo);
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

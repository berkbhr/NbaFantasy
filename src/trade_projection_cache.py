"""Bounded exact projection reuse within one frozen trade-search context.

An optimized lineup depends on its opponent. Pair results therefore include
both rosters; single-roster distributions also include their exact category
weights. This is memoization, not a fixed-opponent lineup approximation.
"""

import hashlib
import pickle
from collections import OrderedDict

import pandas as pd


def _digest(value):
    return hashlib.sha256(pickle.dumps(value, protocol=5)).digest()


def _ids(roster):
    return tuple(sorted(set(roster), key=str))


def _dates(values, roster):
    return tuple((pid, str(pd.Timestamp(values[pid]))) for pid in roster if pid in (values or {}))


class TradeProjectionCache:
    """One search owns this object; never share it across concurrent searches.

    Binding hashes the original (unmodified) context engine once per evaluated
    package. Reusing an object after changing its posteriors, NBA schedule or
    model policy clears all cached results. Bundle-specific engine settings are
    keyed separately. Entry and combined payload-byte limits bound history.
    Values are serialized directly from this process's own projections; no
    external pickle payload or file is accepted by this cache.
    """

    def __init__(self, max_pairs=256, max_distributions=1024, max_payload_bytes=64 * 1024 * 1024):
        if (
            type(max_pairs) is not int
            or max_pairs < 1
            or type(max_distributions) is not int
            or max_distributions < 1
            or type(max_payload_bytes) is not int
            or max_payload_bytes < 1
        ):
            raise ValueError("Projection cache capacities must be positive integers")
        self.max_pairs = max_pairs
        self.max_distributions = max_distributions
        self.max_payload_bytes = max_payload_bytes
        self._scope = None
        self._pairs = OrderedDict()
        self._distributions = OrderedDict()
        self._recency = OrderedDict()
        self._payload_bytes = {"pair": 0, "distribution": 0}
        self._peak_payload_bytes = 0
        self._counts = {
            "pair_hits": 0,
            "pair_misses": 0,
            "distribution_hits": 0,
            "distribution_misses": 0,
            "pair_evictions": 0,
            "distribution_evictions": 0,
            "context_resets": 0,
            "payload_evictions": 0,
            "oversized_payload_skips": 0,
        }

    def bind(self, context, *, eligibility=None):
        # Both lineup eligibility and the separate NBA role map participate in
        # the scope, including legacy engines which use one map for both.
        positions = tuple(sorted((eligibility or {}).items(), key=lambda item: str(item[0])))
        scope = (
            id(context),
            context.sync_id,
            context.as_of.isoformat(),
            _digest(context.engine),
            _digest(positions),
        )
        if scope != self._scope:
            if self._scope is not None:
                self._counts["context_resets"] += 1
            self._pairs.clear()
            self._distributions.clear()
            self._recency.clear()
            self._payload_bytes = {"pair": 0, "distribution": 0}
            self._scope = scope
            return True
        return False

    @staticmethod
    def engine_key(engine):
        """Static projection/utility settings after per-bundle eligibility overrides."""
        return _digest(
            {
                name: getattr(engine, name)
                for name in (
                    "pos_dict",
                    "rotation_pos_dict",
                    "team_map",
                    "completed_game_ids",
                    "default_norm_weights",
                    "num_il_slots",
                    "yahoo_il_eligible_ids",
                    "il_eligible_statuses",
                    "consec_dnp_limit",
                    "availability_weighted_lineup",
                    "availability_weighted_draft_lineup",
                    "availability_correlation",
                    "role_covariance_correlation",
                    "evidence_as_of",
                    "use_positional_depth_and_injury_boost",
                    "low_role_boost_cap",
                    "rotation_policy",
                    "objective",
                    "draw_value",
                )
            }
        )

    @staticmethod
    def roster_key(engine, roster, start, end, as_of, starts=None, ends=None):
        ids = _ids(roster)
        return (
            ids,
            str(pd.Timestamp(start)),
            str(pd.Timestamp(end)),
            str(pd.Timestamp(as_of)),
            _dates(starts, ids),
            _dates(ends, ids),
            tuple(pid for pid in ids if pid in engine.yahoo_already_stashed_ids),
        )

    def pair_key(self, engine, engine_key, home, away, start, end, as_of, starts=None, ends=None):
        return (
            engine_key,
            self.roster_key(engine, home, start, end, as_of, starts, ends),
            self.roster_key(engine, away, start, end, as_of, starts, ends),
        )

    def distribution_key(
        self, engine, engine_key, roster, start, end, as_of, starts=None, ends=None, weights=None
    ):
        actual_weights = engine.default_norm_weights if weights is None else weights
        return (
            engine_key,
            self.roster_key(engine, roster, start, end, as_of, starts, ends),
            tuple(sorted(actual_weights.items())),
        )

    def _get(self, storage, key, kind):
        if key not in storage:
            self._counts[kind + "_misses"] += 1
            return None
        self._counts[kind + "_hits"] += 1
        storage.move_to_end(key)
        self._recency.move_to_end((kind, key))
        # These bytes were generated by _put from a trusted local result.
        # Deserializing creates an isolated mutable graph for every caller.
        return pickle.loads(storage[key])

    def _evict(self, kind, key):
        storage = self._pairs if kind == "pair" else self._distributions
        self._payload_bytes[kind] -= len(storage.pop(key))
        del self._recency[kind, key]
        self._counts[kind + "_evictions"] += 1

    def _put(self, storage, key, value, kind, maximum):
        payload = pickle.dumps(value, protocol=5)
        if len(payload) > self.max_payload_bytes:
            if key in storage:
                self._evict(kind, key)
            self._counts["oversized_payload_skips"] += 1
            return
        if key in storage:
            self._payload_bytes[kind] -= len(storage[key])
        storage[key] = payload
        self._payload_bytes[kind] += len(payload)
        storage.move_to_end(key)
        self._recency[kind, key] = None
        self._recency.move_to_end((kind, key))
        if len(storage) > maximum:
            self._evict(kind, next(iter(storage)))
        while sum(self._payload_bytes.values()) > self.max_payload_bytes:
            old_kind, old_key = next(iter(self._recency))
            self._evict(old_kind, old_key)
            self._counts["payload_evictions"] += 1
        self._peak_payload_bytes = max(self._peak_payload_bytes, sum(self._payload_bytes.values()))

    def get_pair(self, key):
        return self._get(self._pairs, key, "pair")

    def put_pair(self, key, value):
        self._put(self._pairs, key, value, "pair", self.max_pairs)

    def get_distribution(self, key):
        return self._get(self._distributions, key, "distribution")

    def put_distribution(self, key, value):
        self._put(self._distributions, key, value, "distribution", self.max_distributions)

    def stats(self):
        return {
            **self._counts,
            "pair_entries": len(self._pairs),
            "distribution_entries": len(self._distributions),
            "max_pairs": self.max_pairs,
            "max_distributions": self.max_distributions,
            "pair_payload_bytes": self._payload_bytes["pair"],
            "distribution_payload_bytes": self._payload_bytes["distribution"],
            "payload_bytes": sum(self._payload_bytes.values()),
            "peak_payload_bytes": self._peak_payload_bytes,
            "max_payload_bytes": self.max_payload_bytes,
        }

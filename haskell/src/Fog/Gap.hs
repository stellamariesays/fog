-- | A single gap in an agent's knowledge.
--
-- Confidence decays exponentially with time since last seen.
-- STALE gaps carry an additional ×0.5 penalty — they were known once.
module Fog.Gap
  ( GapKind(..)
  , Gap(..)
  , newGap
  , effectiveConfidence
  , defaultHalfLife
  ) where

import Data.Map.Strict (Map)
import qualified Data.Map.Strict as Map

-- | Why the gap exists.
data GapKind
  = KnownUnknown    -- ^ The agent knows it doesn't know this.
  | InferredUnknown -- ^ Inferred from mesh topology or seam structure.
  | Stale           -- ^ Once known, now uncertain.
  deriving (Eq, Ord, Show)

-- | A gap in an agent's knowledge map.
data Gap = Gap
  { gapKey        :: String
  , gapKind       :: GapKind
  , gapDomain     :: Maybe String
  , gapConfidence :: Double
  , gapFirstSeen  :: Double         -- ^ POSIX timestamp (seconds)
  , gapLastSeen   :: Double         -- ^ POSIX timestamp (seconds)
  , gapMetadata   :: Map String String
  } deriving (Eq, Show)

-- | Default half-life: 7 days in seconds.
defaultHalfLife :: Double
defaultHalfLife = 7 * 24 * 3600

-- | Construct a gap with full confidence, timestamped at @now@.
newGap :: String -> GapKind -> Maybe String -> Double -> Gap
newGap key kind domain now = Gap
  { gapKey        = key
  , gapKind       = kind
  , gapDomain     = domain
  , gapConfidence = 1.0
  , gapFirstSeen  = now
  , gapLastSeen   = now
  , gapMetadata   = Map.empty
  }

-- | Effective confidence after temporal decay.
--
-- @
-- eff = confidence × exp(−λt)   where λ = ln(2) \/ halfLife
-- @
--
-- A gap unseen for one @halfLife@ period retains half its original confidence.
-- 'Stale' gaps carry an additional ×0.5 penalty.
--
-- This is a pure function — pass @now@ as the current POSIX time in seconds.
effectiveConfidence
  :: Double   -- ^ Current time (POSIX seconds)
  -> Double   -- ^ Half-life in seconds
  -> Gap
  -> Double
effectiveConfidence now halfLife gap =
  let t            = max (now - gapLastSeen gap) 0
      lam          = log 2 / halfLife
      decay        = exp (-(lam * t))
      stalePenalty = if gapKind gap == Stale then 0.5 else 1.0
  in gapConfidence gap * decay * stalePenalty

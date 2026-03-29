defmodule Fog.Map do
  @moduledoc """
  The map of what an agent doesn't know.

  FogMap is an immutable value. Operations return new maps.
  No mutation — fog states are snapshots, not running processes.
  If you need a stateful fog process, wrap this in a GenServer.
  """

  alias Fog.Gap

  @type t :: %__MODULE__{
    agent_id:   String.t(),
    gaps:       %{String.t() => Gap.t()},
    created_at: integer()
  }

  defstruct [:agent_id, gaps: %{}, created_at: nil]

  @doc "Create an empty FogMap for an agent."
  def new(agent_id) do
    %__MODULE__{agent_id: agent_id, created_at: System.system_time(:second)}
  end

  @doc """
  Add a gap to the map. Returns a new FogMap.
  If the gap key already exists, touches it (updates last_seen).
  """
  def add(%__MODULE__{} = fog, key, kind, opts \\ []) do
    full_key = full_key(key, Keyword.get(opts, :domain))
    updated_gaps =
      Map.update(fog.gaps, full_key, Gap.new(full_key, kind, opts), &Gap.touch/1)
    %{fog | gaps: updated_gaps}
  end

  @doc "Remove a gap (fog lifted). Returns {updated_map, :lifted | :not_found}."
  def remove(%__MODULE__{} = fog, key, domain \\ nil) do
    full_key = full_key(key, domain)
    if Map.has_key?(fog.gaps, full_key) do
      {%{fog | gaps: Map.delete(fog.gaps, full_key)}, :lifted}
    else
      {fog, :not_found}
    end
  end

  @doc "Get a specific gap, or nil."
  def get(%__MODULE__{} = fog, key, domain \\ nil) do
    Map.get(fog.gaps, full_key(key, domain))
  end

  @doc "Number of gaps in this map."
  def size(%__MODULE__{} = fog), do: map_size(fog.gaps)

  @doc "Group gaps by domain."
  def by_domain(%__MODULE__{} = fog) do
    Enum.group_by(Map.values(fog.gaps), &(&1.domain || :_global))
  end

  # ── Private ──────────────────────────────────────────────────────────────

  defp full_key(key, nil),    do: key
  defp full_key(key, domain), do: "#{domain}:#{key}"
end

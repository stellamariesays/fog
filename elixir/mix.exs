defmodule Fog.MixProject do
  use Mix.Project

  def project do
    [
      app: :fog,
      version: "0.1.0",
      elixir: "~> 1.15",
      start_permanent: Mix.env() == :prod,
      deps: deps(),
      description: "Epistemic fog mapping for agent meshes",
    ]
  end

  def application do
    [extra_applications: [:logger]]
  end

  defp deps do
    []
  end
end

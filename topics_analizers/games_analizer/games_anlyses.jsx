import { useEffect, useState } from "react";

const STEAMSPY_BASE = "/steamspy/api.php?request=all";

const formatNumber = (value) =>
	new Intl.NumberFormat("pt-BR").format(Number(value) || 0);

export default function SteamSpyTopGames() {
	const [games, setGames] = useState([]);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState(null);
	const [totalCount, setTotalCount] = useState(0);

	useEffect(() => {
		let active = true;
		setLoading(true);
		setError(null);

		fetch(STEAMSPY_BASE)
			.then((res) => {
				if (!res.ok) {
					throw new Error("Falha ao buscar dados da SteamSpy");
				}
				return res.json();
			})
			.then((data) => {
				if (!active) return;
				const merged = Object.values(data || {}).filter(
					(item) => item && item.name,
				);
				setTotalCount(merged.length);
				const list = merged
					.sort((a, b) => (b.players_2weeks || 0) - (a.players_2weeks || 0))
					.map((item, index) => ({
						appid: item.appid,
						name: item.name,
						rank: index + 1,
						ccu: item.ccu ?? 0,
						players_2weeks: item.players_2weeks ?? 0,
					}));
				setGames(list);
			})
			.catch((err) => {
				if (!active) return;
				setError(err.message || "Erro inesperado");
			})
			.finally(() => {
				if (!active) return;
				setLoading(false);
			});

		return () => {
			active = false;
		};
	}, []);

	const handleExport = () => {
		const payload = JSON.stringify(games, null, 2);
		const blob = new Blob([payload], { type: "application/json" });
		const url = URL.createObjectURL(blob);
		const link = document.createElement("a");
		link.href = url;
		link.download = "steamspy-all-top1000.json";
		link.click();
		URL.revokeObjectURL(url);
	};

	return (
		<div
			style={{
				minHeight: "100vh",
				background: "#0d0d1a",
				color: "#e2e8f0",
			}}
		>
			<div
				style={{
					maxWidth: 1200,
					margin: "0 auto",
					padding: "28px 32px 48px",
				}}
			>
				<header style={{ marginBottom: 24 }}>
					<div
						style={{
							fontSize: 11,
							color: "#64748b",
							letterSpacing: 3,
							textTransform: "uppercase",
							marginBottom: 6,
						}}
					>
						SteamSpy · All · Top 1000 (2 semanas)
					</div>
					<h1
						style={{
							fontSize: 26,
							fontWeight: 700,
							margin: "0 0 6px",
							color: "#f8fafc",
						}}
					>
						Jogos mais populares
					</h1>
					<p style={{ color: "#94a3b8", fontSize: 13, margin: 0 }}>
						Dados em tempo real via SteamSpy. Sem backend.
					</p>
					<p style={{ color: "#64748b", fontSize: 12, margin: "6px 0 0" }}>
						Total no endpoint: {formatNumber(totalCount)} · Exibindo: {formatNumber(games.length)}
					</p>
				</header>

				<div style={{ marginBottom: 16 }}>
					<button
						onClick={handleExport}
						disabled={!games.length}
						style={{
							padding: "8px 14px",
							borderRadius: 6,
							border: "1px solid #1e3a5f",
							background: "#13172a",
							color: "#e2e8f0",
							fontSize: 12,
							cursor: games.length ? "pointer" : "not-allowed",
						}}
					>
						Exportar JSON
					</button>
				</div>

				{loading && (
					<div
						style={{
							background: "#13172a",
							border: "1px solid #1e3a5f",
							borderRadius: 8,
							padding: "10px 14px",
							fontSize: 12,
							color: "#94a3b8",
						}}
					>
						Carregando jogos...
					</div>
				)}

				{error && (
					<div
						style={{
							background: "#2a1116",
							border: "1px solid #ef444440",
							borderRadius: 8,
							padding: "10px 14px",
							fontSize: 12,
							color: "#fecaca",
						}}
					>
						{error}
					</div>
				)}

				<div
					style={{
						display: "grid",
						gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
						gap: 12,
						marginTop: 16,
					}}
				>
					{games.map((game) => (
						<div
							key={game.appid}
							style={{
								background: "#13172a",
								border: "1px solid #1e3a5f",
								borderRadius: 10,
								padding: "12px 14px",
							}}
						>
							<div
								style={{
									display: "flex",
									justifyContent: "space-between",
									fontSize: 11,
									color: "#64748b",
									marginBottom: 6,
								}}
							>
								<span>Rank #{game.rank}</span>
								<span>AppID {game.appid}</span>
							</div>
							<div
								style={{
									fontSize: 14,
									fontWeight: 700,
									color: "#f8fafc",
									marginBottom: 10,
								}}
							>
								{game.name}
							</div>
							<div
								style={{
									display: "grid",
									gap: 6,
									fontSize: 12,
									color: "#94a3b8",
								}}
							>
								<div
									style={{
										display: "flex",
										justifyContent: "space-between",
									}}
								>
									<span>Jogadores ativos</span>
									<span style={{ color: "#e2e8f0", fontWeight: 600 }}>
										{formatNumber(game.ccu)}
									</span>
								</div>
								<div
									style={{
										display: "flex",
										justifyContent: "space-between",
									}}
								>
									<span>Popularidade (2 semanas)</span>
									<span style={{ color: "#e2e8f0", fontWeight: 600 }}>
										{formatNumber(game.players_2weeks)}
									</span>
								</div>
							</div>
						</div>
					))}
				</div>
			</div>
		</div>
	);
}

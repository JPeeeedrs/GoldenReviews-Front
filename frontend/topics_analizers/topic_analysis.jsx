import groupedTopics from "./grouped_topics_llm.json";
import React, { useState, useMemo } from "react";

export default function TopicAnalysis() {
	const [search, setSearch] = useState("");
	const [sortBy, setSortBy] = useState("count");

	const counts = useMemo(() => {
		const map = {};
		for (const theme of Object.values(groupedTopics)) {
			map[theme] = (map[theme] || 0) + 1;
		}
		return map;
	}, []);

	const total = Object.keys(groupedTopics).length;
	const maxCount = Math.max(...Object.values(counts));

	const rows = useMemo(() => {
		let entries = Object.entries(counts).filter(([name]) =>
			name.toLowerCase().includes(search.toLowerCase()),
		);
		if (sortBy === "count") entries.sort((a, b) => b[1] - a[1]);
		else entries.sort((a, b) => a[0].localeCompare(b[0]));
		return entries;
	}, [counts, search, sortBy]);

	const discarded = counts["Lixo / Descartados"] || 0;

	return (
		<div style={{ padding: "20px", color: "white" }}>
			<h1>Painel de Análise de Tópicos</h1>
			<p>Contagem de IDs por macro-tema classificado pela IA.</p>

			{/* Cards de resumo */}
			<div
				style={{
					display: "grid",
					gridTemplateColumns: "repeat(4, 1fr)",
					gap: 12,
					marginBottom: 24,
				}}
			>
				{[
					{ label: "Total de IDs", value: total },
					{ label: "Temas distintos", value: Object.keys(counts).length },
					{ label: "Descartados", value: discarded },
					{ label: "IDs válidos", value: total - discarded },
				].map(({ label, value }) => (
					<div
						key={label}
						style={{ background: "#1e1e24", borderRadius: 8, padding: 16 }}
					>
						<p style={{ margin: 0, fontSize: 12, color: "#aaa" }}>{label}</p>
						<p style={{ margin: 0, fontSize: 24, fontWeight: 500 }}>{value}</p>
					</div>
				))}
			</div>

			{/* Filtros */}
			<div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
				<input
					value={search}
					onChange={(e) => setSearch(e.target.value)}
					placeholder='Filtrar tema...'
					style={{
						flex: 1,
						padding: "8px 12px",
						borderRadius: 6,
						border: "1px solid #444",
						background: "#1e1e24",
						color: "white",
					}}
				/>
				<select
					value={sortBy}
					onChange={(e) => setSortBy(e.target.value)}
					style={{
						padding: "8px 12px",
						borderRadius: 6,
						border: "1px solid #444",
						background: "#1e1e24",
						color: "white",
					}}
				>
					<option value='count'>Ordenar por contagem</option>
					<option value='alpha'>Ordenar por nome</option>
				</select>
			</div>

			{/* Lista de temas */}
			{rows.map(([name, count]) => {
				const pct = ((count / total) * 100).toFixed(1);
				const barW = Math.round((count / maxCount) * 100);
				return (
					<div
						key={name}
						style={{
							display: "flex",
							alignItems: "center",
							gap: 10,
							marginBottom: 8,
							padding: "10px 14px",
							background: "#1e1e24",
							borderRadius: 8,
						}}
					>
						<span style={{ width: 200, flexShrink: 0 }}>{name}</span>
						<div
							style={{
								flex: 1,
								background: "#2a2a35",
								borderRadius: 4,
								height: 10,
								overflow: "hidden",
							}}
						>
							<div
								style={{
									width: `${barW}%`,
									height: "100%",
									background: "#f8b10b",
									borderRadius: 4,
								}}
							/>
						</div>
						<span style={{ minWidth: 36, textAlign: "right", fontWeight: 500 }}>
							{count}
						</span>
						<span
							style={{
								minWidth: 48,
								textAlign: "right",
								fontSize: 12,
								color: "#aaa",
							}}
						>
							{pct}%
						</span>
					</div>
				);
			})}
		</div>
	);
}

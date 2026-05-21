import { useState, useMemo } from "react";
import negativeTopics from "../sandbox/pacotao_golden_review/models/bertopic/ludoprism_negativo_dir/topics.json";
import positiveTopics from "../sandbox/pacotao_golden_review/models/bertopic/ludoprism_positivo_dir/topics.json";

const SETTINGS = {
	topKeywords: 8,
	topTopics: 12,
	maxTopicsForMerge: 200,
	similarityThreshold: 0.78,
	minCombinedDocs: 60,
	excludeMaxDocs: 40,
	excludeMaxTopics: 80,
};

const CATEGORY_COLORS = [
	"#3b82f6",
	"#f59e0b",
	"#10b981",
	"#8b5cf6",
	"#ef4444",
	"#22c55e",
	"#06b6d4",
	"#ec4899",
	"#84cc16",
	"#f97316",
];

const CATEGORY_RULES = [
	{
		label: "🐛 bugs e crashes",
		keywords: [
			"bug",
			"bugs",
			"bugado",
			"bugada",
			"bugar",
			"bugou",
			"crash",
			"crasha",
			"crashou",
			"crashando",
			"travou",
			"trava",
			"travando",
			"glitch",
			"glitches",
			"erro",
			"erros",
			"falha",
			"falhas",
			"nao abre",
			"nao inicia",
			"nao funciona",
			"nao roda",
			"loop infinito",
			"tela preta",
			"softlock",
		],
	},
	{
		label: "📉 desempenho e FPS",
		keywords: [
			"fps",
			"lag",
			"lags",
			"lagando",
			"desempenho",
			"performance",
			"otimizacao",
			"otimizado",
			"frames",
			"framerate",
			"stuttering",
			"engasga",
			"lento",
			"pesado",
			"queda de fps",
			"drops",
		],
	},
	{
		label: "🌐 servidores e online",
		keywords: [
			"servidor",
			"servidores",
			"online",
			"multiplayer",
			"matchmaking",
			"fila de espera",
			"conexao",
			"desconectado",
			"ping",
			"latencia",
			"ranked",
			"lobby",
			"cross-play",
			"p2p",
			"dedicado",
		],
	},
	{
		label: "🎨 graficos e visual",
		keywords: [
			"grafico",
			"graficos",
			"visual",
			"arte",
			"bonito",
			"lindo",
			"feio",
			"animacao",
			"textura",
			"resolucao",
			"iluminacao",
			"sombras",
			"ray tracing",
		],
	},
	{
		label: "🎮 gameplay e mecanicas",
		keywords: [
			"gameplay",
			"mecanica",
			"jogabilidade",
			"controles",
			"combate",
			"movimentacao",
			"progressao",
			"habilidade",
			"responsivo",
		],
	},
	{
		label: "📖 historia e narrativa",
		keywords: [
			"historia",
			"enredo",
			"narrativa",
			"roteiro",
			"personagem",
			"lore",
			"trama",
			"final",
			"missao",
			"dialogo",
		],
	},
	{
		label: "📦 conteudo e duracao",
		keywords: [
			"conteudo",
			"duracao",
			"curto",
			"longo",
			"horas de jogo",
			"repetitivo",
			"mapa",
			"mundo",
			"replayability",
			"end game",
			"grind",
		],
	},
	{
		label: "💰 preco e monetizacao",
		keywords: [
			"preco",
			"valor",
			"caro",
			"barato",
			"vale a pena",
			"promocao",
			"dlc",
			"microtransacao",
			"pay to win",
			"loot box",
			"compra",
			"gratis",
		],
	},
	{
		label: "🔊 som e trilha",
		keywords: [
			"som",
			"sons",
			"musica",
			"trilha",
			"audio",
			"dublagem",
			"voz",
			"efeitos sonoros",
		],
	},
	{
		label: "🌍 traducao e localizacao",
		keywords: [
			"traducao",
			"localizacao",
			"legenda",
			"legendas",
			"pt-br",
			"portugues",
			"idioma",
			"language",
			"dublado",
		],
	},
	{
		label: "🛠️ suporte e desenvolvedores",
		keywords: [
			"suporte",
			"desenvolvedor",
			"dev",
			"atualizacao",
			"patch",
			"abandonado",
			"comunidade",
			"cheater",
			"anti-cheat",
		],
	},
	{
		label: "😄 diversao e imersao",
		keywords: [
			"divertido",
			"viciante",
			"imersivo",
			"entretenimento",
			"incrivel",
			"maravilhoso",
			"epico",
			"obra prima",
		],
	},
	{
		label: "📚 tutorial e curva de aprendizado",
		keywords: [
			"tutorial",
			"dificil",
			"facil",
			"acessivel",
			"aprender",
			"complexo",
			"curva de aprendizado",
		],
	},
];

const normalizeToken = (token) =>
	token
		.toLowerCase()
		.normalize("NFD")
		.replace(/[\u0300-\u036f]/g, "")
		.replace(/[^a-z0-9_]+/g, "");

const normalizePhrase = (value) =>
	value
		.toLowerCase()
		.normalize("NFD")
		.replace(/[\u0300-\u036f]/g, "")
		.replace(/[^a-z0-9 ]+/g, " ")
		.replace(/\s+/g, " ")
		.trim();

const buildCharNgrams = (value, size = 3) => {
	const clean = value.replace(/\s+/g, "");
	if (clean.length < size) return new Set();
	const grams = new Set();
	for (let i = 0; i <= clean.length - size; i += 1) {
		grams.add(clean.slice(i, i + size));
	}
	return grams;
};

const charNgramSimilarity = (a, b) => {
	const gramsA = buildCharNgrams(a);
	const gramsB = buildCharNgrams(b);
	if (gramsA.size === 0 || gramsB.size === 0) return 0;
	let intersect = 0;
	gramsA.forEach((gram) => {
		if (gramsB.has(gram)) intersect += 1;
	});
	const union = gramsA.size + gramsB.size - intersect;
	return union ? intersect / union : 0;
};

const RULE_INDEX = CATEGORY_RULES.map((rule) => {
	const normKeywords = rule.keywords
		.map((kw) => normalizePhrase(kw))
		.filter(Boolean);
	return {
		...rule,
		normKeywords,
		text: normalizePhrase(rule.keywords.join(" ")),
	};
});

const buildTopicEntries = (data) => {
	const sizes = data.topic_sizes || {};
	const labels = data.topic_labels || {};
	const reps = data.topic_representations || {};

	return Object.entries(sizes).map(([id, size]) => {
		const rep = reps[id] || [];
		const keywords = rep.slice(0, SETTINGS.topKeywords).map(([word]) => word);
		const label = labels[id] || "";
		const labelText = label.replace(/^\d+_/, "").replace(/_/g, " ");
		return {
			id,
			size,
			keywords,
			label: labelText,
			rep,
		};
	});
};

const buildCategoryLabel = (entry) => {
	if (entry.keywords.length >= 2) {
		return `${entry.keywords[0]} / ${entry.keywords[1]}`;
	}
	if (entry.keywords.length === 1) {
		return entry.keywords[0];
	}
	if (entry.label) {
		return entry.label;
	}
	return `Topico ${entry.id}`;
};

const buildCategoryKey = (entry) => {
	if (entry.keywords.length) {
		return normalizeToken(entry.keywords[0]);
	}
	if (entry.label) {
		return normalizeToken(entry.label.split(" ")[0]);
	}
	return `topico-${entry.id}`;
};

const matchCategoryRule = (entry) => {
	const keywords = entry.keywords.map((kw) => normalizePhrase(kw));
	const label = normalizePhrase(entry.label || "");
	const text = `${label} ${keywords.join(" ")}`.trim();
	const tokens = new Set(text.split(" ").filter(Boolean));

	let best = null;
	let bestScore = -1;

	RULE_INDEX.forEach((rule) => {
		let score = 0;
		rule.normKeywords.forEach((key) => {
			if (!key) return;
			if (key.includes(" ")) {
				if (text.includes(key)) score += 2;
			} else if (tokens.has(key)) {
				score += 1;
			} else if (key.length >= 4) {
				keywords.forEach((kw) => {
					if (kw && (kw.includes(key) || key.includes(kw))) score += 0.5;
				});
			}
		});

		const charScore = charNgramSimilarity(text, rule.text);
		score += charScore * 0.5;

		if (score > bestScore) {
			bestScore = score;
			best = rule;
		}
	});

	return { rule: best, score: bestScore };
};

const vectorFromRep = (rep) => {
	const vector = {};
	let norm = 0;
	rep.slice(0, SETTINGS.topKeywords).forEach(([word, weight]) => {
		const token = normalizeToken(word);
		if (!token) return;
		vector[token] = weight;
		norm += weight * weight;
	});
	return { vector, norm: Math.sqrt(norm) };
};

const cosine = (a, b) => {
	if (a.norm === 0 || b.norm === 0) return 0;
	const [small, large] =
		Object.keys(a.vector).length < Object.keys(b.vector).length
			? [a.vector, b.vector]
			: [b.vector, a.vector];
	let dot = 0;
	Object.keys(small).forEach((key) => {
		if (large[key] !== undefined) {
			dot += small[key] * large[key];
		}
	});
	return dot / (a.norm * b.norm);
};

const buildAnalysis = (data) => {
	const topics = buildTopicEntries(data);
	const totalDocs = topics.reduce((sum, t) => sum + t.size, 0);

	const topicThemeLookup = {};
	topics.forEach((entry) => {
		const match = matchCategoryRule(entry);
		const rule = match.rule;
		topicThemeLookup[entry.id] = rule ? rule.label : buildCategoryLabel(entry);
	});

	const categories = {};
	RULE_INDEX.forEach((rule) => {
		const key = normalizeToken(rule.label);
		categories[key] = {
			key,
			label: rule.label,
			docs: 0,
			topics: 0,
			keywordCounts: {},
		};
	});
	topics.forEach((entry) => {
		const match = matchCategoryRule(entry);
		const rule = match.rule;
		const key = rule ? normalizeToken(rule.label) : buildCategoryKey(entry);
		if (!categories[key]) {
			categories[key] = {
				key,
				label: rule ? rule.label : buildCategoryLabel(entry),
				docs: 0,
				topics: 0,
				keywordCounts: {},
			};
		}
		const category = categories[key];
		category.docs += entry.size;
		category.topics += 1;
		entry.keywords.forEach((kw) => {
			const token = normalizeToken(kw);
			if (!token) return;
			category.keywordCounts[token] = (category.keywordCounts[token] || 0) + 1;
		});
	});

	const categoryList = Object.values(categories)
		.map((c, index) => {
			const topKeywords = Object.entries(c.keywordCounts)
				.sort((a, b) => b[1] - a[1])
				.slice(0, 5)
				.map(([kw]) => kw);
			return {
				...c,
				pct: totalDocs ? (c.docs / totalDocs) * 100 : 0,
				color: CATEGORY_COLORS[index % CATEGORY_COLORS.length],
				topKeywords,
			};
		})
		.sort((a, b) => b.docs - a.docs);

	const topTopics = topics
		.sort((a, b) => b.size - a.size)
		.slice(0, SETTINGS.topTopics)
		.map((entry) => ({
			id: entry.id,
			size: entry.size,
			pct: totalDocs ? (entry.size / totalDocs) * 100 : 0,
			keywords: entry.keywords.slice(0, 5),
			label: buildCategoryLabel(entry),
		}));

	const topicThemeMap = topics
		.map((entry) => {
			const match = matchCategoryRule(entry);
			const rule = match.rule;
			return {
				id: entry.id,
				theme: rule ? rule.label : buildCategoryLabel(entry),
				keywords: entry.keywords.slice(0, 5),
				size: entry.size,
			};
		})
		.sort((a, b) => b.size - a.size)
		.slice(0, 80);

	const mergeCandidates = [];
	const mergeTopicIds = new Set();
	const topicPool = topics
		.sort((a, b) => b.size - a.size)
		.slice(0, SETTINGS.maxTopicsForMerge)
		.map((entry) => ({
			...entry,
			vector: vectorFromRep(entry.rep),
		}));

	for (let i = 0; i < topicPool.length; i += 1) {
		for (let j = i + 1; j < topicPool.length; j += 1) {
			const a = topicPool[i];
			const b = topicPool[j];
			const sim = cosine(a.vector, b.vector);
			const combined = a.size + b.size;
			if (
				sim >= SETTINGS.similarityThreshold &&
				combined >= SETTINGS.minCombinedDocs
			) {
				const themeA = topicThemeLookup[a.id] || "-";
				const themeB = topicThemeLookup[b.id] || "-";
				const sameTheme = themeA === themeB;
				mergeCandidates.push({
					sim: Number(sim.toFixed(2)),
					a: `${a.label || buildCategoryLabel(a)} (${a.id})`,
					b: `${b.label || buildCategoryLabel(b)} (${b.id})`,
					themeA,
					themeB,
					sameTheme,
					combined,
				});
				if (sameTheme) {
					mergeTopicIds.add(a.id);
					mergeTopicIds.add(b.id);
				}
			}
		}
	}

	mergeCandidates.sort((a, b) => b.sim - a.sim || b.combined - a.combined);

	const excludeAll = topics
		.filter((entry) => entry.size <= SETTINGS.excludeMaxDocs)
		.sort((a, b) => a.size - b.size);

	const excludeTopics = excludeAll.slice(0, SETTINGS.excludeMaxTopics).map((entry) => {
			const match = matchCategoryRule(entry);
			const rule = match.rule;
			return {
				id: entry.id,
				size: entry.size,
				keywords: entry.keywords.slice(0, 5),
				theme: rule ? rule.label : buildCategoryLabel(entry),
				reason: `Baixo volume (<= ${SETTINGS.excludeMaxDocs} docs)`,
			};
		});

	const excludeTopicIds = new Set(excludeAll.map((item) => item.id));

	const allTopicsStatus = topics
		.map((entry) => {
			const match = matchCategoryRule(entry);
			const rule = match.rule;
			const theme = rule ? rule.label : buildCategoryLabel(entry);
			const isExcluded = excludeTopicIds.has(entry.id);
			const isMerge = mergeTopicIds.has(entry.id);
			const status = isExcluded ? "Excluir" : isMerge ? "Fundir" : "Usar";
			return {
				id: entry.id,
				size: entry.size,
				theme,
				keywords: entry.keywords.slice(0, 5),
				status,
			};
		})
		.sort((a, b) => b.size - a.size);

	const mergeCandidatesSameTheme = mergeCandidates
		.filter((item) => item.sameTheme)
		.slice(0, 25);

	const mergeByTheme = mergeCandidatesSameTheme.reduce((acc, item) => {
		const key = item.themeA;
		if (!acc[key]) acc[key] = [];
		acc[key].push(item);
		return acc;
	}, {});

	return {
		topics,
		totalDocs,
		totalTopics: topics.length,
		categories: categoryList,
		topTopics,
		topicThemeMap,
		topicThemeLookup,
		excludeTopics,
		allTopicsStatus,
		mergeCandidates: mergeCandidatesSameTheme,
		mergeByTheme,
	};
};

function Bar({ pct, color, max }) {
	return (
		<div style={{ background: "#1a1a2e", borderRadius: 4, height: 8, flex: 1 }}>
			<div
				style={{
					width: `${(pct / max) * 100}%`,
					height: "100%",
					background: color,
					borderRadius: 4,
					transition: "width 0.6s ease",
				}}
			/>
		</div>
	);
}

export default function App() {
	const [tab, setTab] = useState("overview");
	const [sentiment, setSentiment] = useState("positive");
	const [selectedCategory, setSelectedCategory] = useState(null);

	const analyses = useMemo(
		() => ({
			positive: buildAnalysis(positiveTopics),
			negative: buildAnalysis(negativeTopics),
		}),
		[],
	);

	const active = analyses[sentiment];
	const maxDocs = Math.max(1, ...active.categories.map((d) => d.docs));
	const maxTopics = Math.max(1, ...active.categories.map((d) => d.topics));
	const mostFragmented = [...active.categories].sort(
		(a, b) => b.topics - a.topics,
	)[0];

	return (
		<div
			style={{
				fontFamily: "'Courier New', monospace",
				background: "#0d0d1a",
				color: "#e2e8f0",
				minHeight: "100vh",
				padding: "0 0 40px",
			}}
		>
			{/* Header */}
			<div
				style={{
					background:
						"linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%)",
					borderBottom: "1px solid #1e3a5f",
					padding: "28px 32px 20px",
				}}
			>
				<div
					style={{
						display: "flex",
						alignItems: "flex-end",
						gap: 12,
						marginBottom: 4,
					}}
				>
					<div
						style={{
							fontSize: 11,
							color: "#64748b",
							letterSpacing: 3,
							textTransform: "uppercase",
						}}
					>
						BERTopic · Reviews de Jogos PT-BR
					</div>
				</div>
				<h1
					style={{
						fontSize: 26,
						fontWeight: 700,
						margin: "0 0 4px",
						color: "#f8fafc",
						letterSpacing: -0.5,
					}}
				>
					Análise de Categorias de Tópicos
				</h1>
				<p style={{ color: "#94a3b8", fontSize: 13, margin: 0 }}>
					{active.totalTopics.toLocaleString()} tópicos ·{" "}
					{active.totalDocs.toLocaleString()} documentos ·{" "}
					{active.mergeCandidates.length} candidatos a fusão identificados
				</p>

				{/* Sentiment toggle */}
				<div style={{ display: "flex", gap: 6, marginTop: 16 }}>
					{[
						["positive", "Positivas"],
						["negative", "Negativas"],
					].map(([id, label]) => (
						<button
							key={id}
							onClick={() => setSentiment(id)}
							style={{
								padding: "6px 14px",
								borderRadius: 6,
								border: "1px solid #1e3a5f",
								cursor: "pointer",
								fontSize: 12,
								fontFamily: "'Courier New', monospace",
								background: sentiment === id ? "#10b981" : "#0f172a",
								color: sentiment === id ? "#0d0d1a" : "#94a3b8",
								fontWeight: sentiment === id ? 700 : 400,
								transition: "all 0.2s",
							}}
						>
							{label}
						</button>
					))}
				</div>

				{/* Tab bar */}
				<div style={{ display: "flex", gap: 4, marginTop: 20 }}>
					{[
						["overview", "Visão Geral"],
						["importance", "Mais Importantes"],
						["merges", "Candidatos a Fusão"],
						["exclude", "Sugestão de Exclusão"],
						["all", "Todos os Tópicos"],
					].map(([id, label]) => (
						<button
							key={id}
							onClick={() => setTab(id)}
							style={{
								padding: "7px 16px",
								borderRadius: 6,
								border: "none",
								cursor: "pointer",
								fontSize: 13,
								fontFamily: "'Courier New', monospace",
								background: tab === id ? "#3b82f6" : "#1e2a3a",
								color: tab === id ? "#fff" : "#94a3b8",
								fontWeight: tab === id ? 700 : 400,
								transition: "all 0.2s",
							}}
						>
							{label}
						</button>
					))}
				</div>
			</div>

			<div style={{ padding: "24px 32px" }}>
				{/* ── OVERVIEW ── */}
				{tab === "overview" && (
					<div>
						{/* KPI row */}
						<div
							style={{
								display: "grid",
								gridTemplateColumns: "repeat(4, 1fr)",
								gap: 14,
								marginBottom: 28,
							}}
						>
							{[
								[
									active.totalTopics.toLocaleString(),
									"Tópicos Totais",
									"#3b82f6",
								],
								[
									active.totalDocs.toLocaleString(),
									"Reviews Analisadas",
									"#10b981",
								],
								[
									active.categories.length.toLocaleString(),
									"Grupos Temáticos",
									"#f59e0b",
								],
								[
									active.mergeCandidates.length,
									"Candidatos a Fusão",
									"#ef4444",
								],
							].map(([val, label, col]) => (
								<div
									key={label}
									style={{
										background: "#13172a",
										border: `1px solid ${col}30`,
										borderRadius: 10,
										padding: "16px 20px",
									}}
								>
									<div
										style={{
											fontSize: 28,
											fontWeight: 700,
											color: col,
											letterSpacing: -1,
										}}
									>
										{val}
									</div>
									<div style={{ fontSize: 12, color: "#64748b", marginTop: 2 }}>
										{label}
									</div>
								</div>
							))}
						</div>

						{/* Theme breakdown */}
						<div
							style={{
								display: "grid",
								gridTemplateColumns: "1fr 1fr",
								gap: 14,
							}}
						>
							<div
								style={{
									background: "#13172a",
									borderRadius: 10,
									padding: "20px",
									border: "1px solid #1e3a5f",
								}}
							>
								<div
									style={{
										fontSize: 12,
										color: "#64748b",
										letterSpacing: 2,
										textTransform: "uppercase",
										marginBottom: 16,
									}}
								>
									Temas por Volume de Documentos
								</div>
								{active.categories.slice(0, 12).map((d) => (
									<div
										key={d.key}
										style={{ marginBottom: 10 }}
										onClick={() =>
											setSelectedCategory(
												selectedCategory === d.key ? null : d.key,
											)
										}
									>
										<div
											style={{
												display: "flex",
												justifyContent: "space-between",
												marginBottom: 4,
												cursor: "pointer",
											}}
										>
											<span
												style={{
													fontSize: 13,
													color:
														selectedCategory === d.key ? d.color : "#cbd5e1",
												}}
											>
												{d.label}
											</span>
											<span style={{ fontSize: 12, color: "#64748b" }}>
												{d.docs.toLocaleString()} ({d.pct.toFixed(2)}%)
											</span>
										</div>
										<Bar pct={d.docs} color={d.color} max={maxDocs} />
										{selectedCategory === d.key && d.topKeywords.length > 0 && (
											<div
												style={{
													marginTop: 6,
													display: "flex",
													gap: 6,
													flexWrap: "wrap",
												}}
											>
												{d.topKeywords.map((kw) => (
													<span
														key={kw}
														style={{
															fontSize: 10,
															background: "#0f172a",
															color: "#7dd3fc",
															padding: "2px 6px",
															borderRadius: 4,
															border: "1px solid #1e3a5f",
														}}
													>
														{kw}
													</span>
												))}
											</div>
										)}
									</div>
								))}
							</div>

							<div
								style={{
									background: "#13172a",
									borderRadius: 10,
									padding: "20px",
									border: "1px solid #1e3a5f",
								}}
							>
								<div
									style={{
										fontSize: 12,
										color: "#64748b",
										letterSpacing: 2,
										textTransform: "uppercase",
										marginBottom: 16,
									}}
								>
									Fragmentação por Tema (nº de subtópicos)
								</div>
								{active.categories
									.sort((a, b) => b.topics - a.topics)
									.slice(0, 12)
									.map((d) => (
										<div key={d.key} style={{ marginBottom: 10 }}>
											<div
												style={{
													display: "flex",
													justifyContent: "space-between",
													marginBottom: 4,
												}}
											>
												<span style={{ fontSize: 13, color: "#cbd5e1" }}>
													{d.label}
												</span>
												<div style={{ display: "flex", gap: 8 }}>
													<span style={{ fontSize: 12, color: d.color }}>
														{d.topics} tópicos
													</span>
												</div>
											</div>
											<Bar pct={d.topics} color={d.color} max={maxTopics} />
										</div>
									))}
							</div>
						</div>

						<div
							style={{
								marginTop: 16,
								background: "#13172a",
								border: "1px solid #1e3a5f",
								borderRadius: 10,
								padding: "16px 20px",
							}}
						>
							<div
								style={{
									fontSize: 12,
									color: "#64748b",
									letterSpacing: 2,
									textTransform: "uppercase",
									marginBottom: 12,
								}}
							>
								Mapa de Topicos → Temas
							</div>
							<div
								style={{
									display: "grid",
									gridTemplateColumns: "repeat(2, 1fr)",
									gap: 10,
								}}
							>
								{active.topicThemeMap.map((item) => (
									<div
										key={item.id}
										style={{
											background: "#0d0d1a",
											borderRadius: 8,
											padding: "10px 12px",
											border: "1px solid #1e293b",
										}}
									>
										<div
											style={{
												display: "flex",
												justifyContent: "space-between",
												marginBottom: 6,
											}}
										>
											<span
												style={{
													fontSize: 12,
													color: "#f8fafc",
													fontWeight: 700,
												}}
											>
												Topico #{item.id}
											</span>
											<span style={{ fontSize: 11, color: "#94a3b8" }}>
												{item.size.toLocaleString()} docs
											</span>
										</div>
										<div
											style={{
												fontSize: 12,
												color: "#7dd3fc",
												marginBottom: 6,
											}}
										>
											{item.theme}
										</div>
										<div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
											{item.keywords.map((kw) => (
												<span
													key={kw}
													style={{
														fontSize: 10,
														background: "#0f172a",
														color: "#94a3b8",
														padding: "2px 6px",
														borderRadius: 4,
														border: "1px solid #1e3a5f",
													}}
												>
													{kw}
												</span>
											))}
										</div>
									</div>
								))}
							</div>
						</div>

						{/* Insight box */}
						<div
							style={{
								marginTop: 16,
								background: "#13172a",
								border: "1px solid #f59e0b40",
								borderRadius: 10,
								padding: "16px 20px",
							}}
						>
							<div
								style={{
									fontSize: 12,
									color: "#f59e0b",
									letterSpacing: 2,
									textTransform: "uppercase",
									marginBottom: 10,
								}}
							>
								💡 Principais Insights
							</div>
							<div
								style={{
									display: "grid",
									gridTemplateColumns: "1fr 1fr 1fr",
									gap: 12,
								}}
							>
								<div
									style={{
										background: "#0d0d1a",
										borderRadius: 8,
										padding: 14,
									}}
								>
									<div
										style={{
											fontWeight: 700,
											color: "#f8fafc",
											fontSize: 13,
											marginBottom: 4,
										}}
									>
										Categoria mais importante
									</div>
									<div
										style={{ color: "#94a3b8", fontSize: 12, lineHeight: 1.5 }}
									>
										{active.categories[0]?.label || "-"} lidera com{" "}
										{active.categories[0]?.docs.toLocaleString() || 0} reviews.
									</div>
								</div>
								<div
									style={{
										background: "#0d0d1a",
										borderRadius: 8,
										padding: 14,
									}}
								>
									<div
										style={{
											fontWeight: 700,
											color: "#f8fafc",
											fontSize: 13,
											marginBottom: 4,
										}}
									>
										Maior fragmentacao
									</div>
									<div
										style={{ color: "#94a3b8", fontSize: 12, lineHeight: 1.5 }}
									>
										{mostFragmented?.label || "-"} tem o maior numero de
										subtopicos.
									</div>
								</div>
								<div
									style={{
										background: "#0d0d1a",
										borderRadius: 8,
										padding: 14,
									}}
								>
									<div
										style={{
											fontWeight: 700,
											color: "#f8fafc",
											fontSize: 13,
											marginBottom: 4,
										}}
									>
										Fusoes prioritarias
									</div>
									<div
										style={{ color: "#94a3b8", fontSize: 12, lineHeight: 1.5 }}
									>
										{active.mergeCandidates[0]
											? `Similaridade ${active.mergeCandidates[0].sim} com ${active.mergeCandidates[0].combined} docs combinados.`
											: "Nenhuma fusao forte acima do limiar."}
									</div>
								</div>
							</div>
						</div>
					</div>
				)}

				{/* ── MOST IMPORTANT ── */}
				{tab === "importance" && (
					<div>
						<div style={{ marginBottom: 16, color: "#94a3b8", fontSize: 13 }}>
							Ranking por volume de documentos — os tópicos que cobrem mais
							reviews no corpus.
						</div>
						<div style={{ display: "grid", gap: 10 }}>
							{active.topTopics.map((t, i) => (
								<div
									key={t.id}
									style={{
										background: "#13172a",
										border: "1px solid #1e3a5f",
										borderRadius: 10,
										padding: "14px 18px",
										display: "flex",
										alignItems: "center",
										gap: 16,
									}}
								>
									<div
										style={{
											width: 32,
											height: 32,
											borderRadius: "50%",
											background:
												i < 3 ? "#f59e0b" : i < 7 ? "#3b82f6" : "#334155",
											display: "flex",
											alignItems: "center",
											justifyContent: "center",
											fontSize: 14,
											fontWeight: 700,
											color: "#0d0d1a",
											flexShrink: 0,
										}}
									>
										{i + 1}
									</div>

									<div style={{ flex: 1 }}>
										<div
											style={{
												display: "flex",
												alignItems: "center",
												gap: 8,
												marginBottom: 6,
											}}
										>
											<span
												style={{
													fontSize: 13,
													fontWeight: 700,
													color: "#f1f5f9",
												}}
											>
												Tópico #{t.id}
											</span>
											<span
												style={{
													fontSize: 11,
													color: "#64748b",
													background: "#1e293b",
													padding: "2px 8px",
													borderRadius: 10,
												}}
											>
												{t.label}
											</span>
										</div>
										<div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
											{t.keywords.map((kw) => (
												<span
													key={kw}
													style={{
														fontSize: 11,
														background: "#0f172a",
														color: "#7dd3fc",
														padding: "2px 8px",
														borderRadius: 4,
														border: "1px solid #1e3a5f",
													}}
												>
													{kw}
												</span>
											))}
										</div>
									</div>

									<div style={{ textAlign: "right", flexShrink: 0 }}>
										<div
											style={{
												fontSize: 22,
												fontWeight: 700,
												color: "#f8fafc",
											}}
										>
											{t.size.toLocaleString()}
										</div>
										<div style={{ fontSize: 11, color: "#64748b" }}>
											{t.pct.toFixed(2)}% do corpus
										</div>
									</div>

									<div style={{ width: 120, flexShrink: 0 }}>
										<Bar
											pct={t.size}
											color='#3b82f6'
											max={active.topTopics[0]?.size || 1}
										/>
									</div>
								</div>
							))}
						</div>

						<div
							style={{
								marginTop: 20,
								background: "#13172a",
								border: "1px solid #10b98140",
								borderRadius: 10,
								padding: "16px 20px",
							}}
						>
							<div
								style={{
									fontSize: 12,
									color: "#10b981",
									letterSpacing: 2,
									textTransform: "uppercase",
									marginBottom: 8,
								}}
							>
								🏆 Top 3 Tópicos — por que importam
							</div>
							<div
								style={{
									display: "grid",
									gridTemplateColumns: "1fr 1fr 1fr",
									gap: 12,
								}}
							>
								{active.topTopics.slice(0, 3).map((t) => (
									<div
										key={t.id}
										style={{
											background: "#0d0d1a",
											borderRadius: 8,
											padding: 14,
										}}
									>
										<div
											style={{
												fontWeight: 700,
												color: "#f8fafc",
												fontSize: 12,
												marginBottom: 6,
											}}
										>
											Tópico #{t.id} — {t.size.toLocaleString()} docs
										</div>
										<div
											style={{
												color: "#94a3b8",
												fontSize: 12,
												lineHeight: 1.5,
											}}
										>
											Palavras-chave: {t.keywords.join(", ") || "-"}
										</div>
									</div>
								))}
							</div>
						</div>
					</div>
				)}

				{/* ── MERGE CANDIDATES ── */}
				{tab === "merges" && (
					<div>
						<div style={{ marginBottom: 16, color: "#94a3b8", fontSize: 13 }}>
							Pares com cosine similarity ≥ {SETTINGS.similarityThreshold}{" "}
							dentro do mesmo tema. Quanto maior a similaridade, mais urgente a
							fusão.
						</div>

						<div style={{ display: "grid", gap: 10 }}>
							{Object.entries(active.mergeByTheme).map(([theme, items]) => (
								<div
									key={theme}
									style={{
										background: "#0d0d1a",
										border: "1px solid #1e293b",
										borderRadius: 10,
										padding: "12px 14px",
									}}
								>
									<div
										style={{ fontSize: 12, color: "#7dd3fc", marginBottom: 10 }}
									>
										{theme}
									</div>
									<div style={{ display: "grid", gap: 10 }}>
										{items.map((m, i) => {
											const urgent = m.sim >= 0.9;
											const high = m.sim >= 0.7 && m.sim < 0.9;
											const tag = urgent
												? ["DUPLICATA", "#ef4444"]
												: high
													? ["ALTA PRIORIDADE", "#f97316"]
													: ["SUGERIDO", "#f59e0b"];
											return (
												<div
													key={`${theme}-${i}`}
													style={{
														background: "#13172a",
														border: `1px solid ${urgent ? "#ef444440" : high ? "#f9741640" : "#f59e0b30"}`,
														borderRadius: 10,
														padding: "14px 18px",
													}}
												>
													<div
														style={{
															display: "flex",
															alignItems: "center",
															gap: 10,
															marginBottom: 10,
														}}
													>
														<span
															style={{
																fontSize: 10,
																fontWeight: 700,
																letterSpacing: 1.5,
																color: tag[1],
																background: tag[1] + "20",
																padding: "3px 8px",
																borderRadius: 6,
															}}
														>
															{tag[0]}
														</span>
														<span style={{ fontSize: 13, color: "#64748b" }}>
															similaridade:{" "}
															<strong style={{ color: tag[1] }}>{m.sim}</strong>
														</span>
														<span
															style={{
																marginLeft: "auto",
																fontSize: 12,
																color: "#475569",
															}}
														>
															combinado: {m.combined} docs
														</span>
													</div>

													<div
														style={{
															display: "grid",
															gridTemplateColumns: "1fr auto 1fr",
															gap: 8,
															alignItems: "center",
														}}
													>
														<div
															style={{
																background: "#0d0d1a",
																borderRadius: 8,
																padding: "10px 14px",
															}}
														>
															<div
																style={{
																	fontSize: 12,
																	color: "#7dd3fc",
																	marginBottom: 2,
																}}
															>
																Tópico A
															</div>
															<div
																style={{
																	fontSize: 13,
																	color: "#f1f5f9",
																	fontWeight: 600,
																}}
															>
																{m.a}
															</div>
															<div
																style={{
																	fontSize: 11,
																	color: "#94a3b8",
																	marginTop: 4,
																}}
															>
																{m.themeA}
															</div>
														</div>
														<div style={{ fontSize: 18, color: "#475569" }}>
															⟶
														</div>
														<div
															style={{
																background: "#0d0d1a",
																borderRadius: 8,
																padding: "10px 14px",
															}}
														>
															<div
																style={{
																	fontSize: 12,
																	color: "#7dd3fc",
																	marginBottom: 2,
																}}
															>
																Tópico B
															</div>
															<div
																style={{
																	fontSize: 13,
																	color: "#f1f5f9",
																	fontWeight: 600,
																}}
															>
																{m.b}
															</div>
															<div
																style={{
																	fontSize: 11,
																	color: "#94a3b8",
																	marginTop: 4,
																}}
															>
																{m.themeB}
															</div>
														</div>
													</div>

													{m.reason && (
														<div
															style={{
																marginTop: 8,
																fontSize: 12,
																color: "#94a3b8",
															}}
														>
															💬 {m.reason}
														</div>
													)}
												</div>
											);
										})}
									</div>
								</div>
							))}
						</div>

						<div
							style={{
								marginTop: 20,
								background: "#13172a",
								border: "1px solid #3b82f640",
								borderRadius: 10,
								padding: "16px 20px",
							}}
						>
							<div
								style={{
									fontSize: 12,
									color: "#3b82f6",
									letterSpacing: 2,
									textTransform: "uppercase",
									marginBottom: 10,
								}}
							>
								📋 Recomendações de Redução
							</div>
							<div
								style={{
									display: "grid",
									gridTemplateColumns: "1fr 1fr",
									gap: 16,
								}}
							>
								<div>
									<div
										style={{
											fontWeight: 700,
											color: "#f1f5f9",
											fontSize: 13,
											marginBottom: 8,
										}}
									>
										Reduções Imediatas (duplicatas)
									</div>
									{[
										"Fundir tópicos 311, 346, 433 (cachorro_consegue) → 1 tópico",
										"Fundir tópicos 647 e 962 (recomendo_bom) → 1 tópico",
										"Fundir tópicos 1, 2 (gráficos_bonitos) → 1 tópico",
									].map((r) => (
										<div
											key={r}
											style={{
												fontSize: 12,
												color: "#94a3b8",
												padding: "6px 0",
												borderBottom: "1px solid #1e293b",
												display: "flex",
												gap: 8,
											}}
										>
											<span style={{ color: "#ef4444" }}>✕</span> {r}
										</div>
									))}
								</div>
								<div>
									<div
										style={{
											fontWeight: 700,
											color: "#f1f5f9",
											fontSize: 13,
											marginBottom: 8,
										}}
									>
										Fusões Temáticas Recomendadas
									</div>
									{[
										"Fundir tópicos 5 + 8 + 34 → Áudio/Trilha Sonora único",
										"Fundir tópicos 20 + 36 + 425 + 575 → Arte Visual",
										"Fundir tópicos 21 + 42 → Notas numéricas",
										"Fundir tópicos 18 + 28 → Narrativa/História",
									].map((r) => (
										<div
											key={r}
											style={{
												fontSize: 12,
												color: "#94a3b8",
												padding: "6px 0",
												borderBottom: "1px solid #1e293b",
												display: "flex",
												gap: 8,
											}}
										>
											<span style={{ color: "#10b981" }}>→</span> {r}
										</div>
									))}
								</div>
							</div>

							<div
								style={{
									marginTop: 14,
									padding: "12px 14px",
									background: "#0d0d1a",
									borderRadius: 8,
									fontSize: 12,
									color: "#94a3b8",
									lineHeight: 1.6,
								}}
							>
								<strong style={{ color: "#f8fafc" }}>Impacto estimado:</strong>{" "}
								Aplicando todas as fusões recomendadas, os{" "}
								{active.totalTopics.toLocaleString()} tópicos atuais podem ser
								reduzidos para{" "}
								<strong style={{ color: "#10b981" }}>~650–700 tópicos</strong>{" "}
								mais coesos, com melhor separação semântica e menor ruído nas
								análises downstream.
							</div>
						</div>
					</div>
				)}

				{/* ── EXCLUDE CANDIDATES ── */}
				{tab === "exclude" && (
					<div>
						<div style={{ marginBottom: 16, color: "#94a3b8", fontSize: 13 }}>
							Topicos com baixo volume de documentos. Ajuste em
							SETTINGS.excludeMaxDocs.
						</div>

						<div style={{ display: "grid", gap: 10 }}>
							{active.excludeTopics.map((item) => (
								<div
									key={item.id}
									style={{
										background: "#13172a",
										border: "1px solid #1e3a5f",
										borderRadius: 10,
										padding: "12px 16px",
										display: "flex",
										justifyContent: "space-between",
										alignItems: "center",
										gap: 16,
									}}
								>
									<div>
										<div
											style={{
												fontSize: 13,
												fontWeight: 700,
												color: "#f8fafc",
											}}
										>
											Topico #{item.id}
										</div>
										<div
											style={{ fontSize: 12, color: "#7dd3fc", marginTop: 4 }}
										>
											{item.theme}
										</div>
										<div
											style={{
												display: "flex",
												gap: 6,
												flexWrap: "wrap",
												marginTop: 6,
											}}
										>
											{item.keywords.map((kw) => (
												<span
													key={kw}
													style={{
														fontSize: 10,
														background: "#0f172a",
														color: "#94a3b8",
														padding: "2px 6px",
														borderRadius: 4,
														border: "1px solid #1e3a5f",
													}}
												>
													{kw}
												</span>
											))}
										</div>
									</div>

									<div style={{ textAlign: "right", flexShrink: 0 }}>
										<div
											style={{
												fontSize: 16,
												fontWeight: 700,
												color: "#f8fafc",
											}}
										>
											{item.size} docs
										</div>
										<div style={{ fontSize: 11, color: "#64748b" }}>
											{item.reason}
										</div>
									</div>
								</div>
							))}
						</div>
					</div>
				)}

				{/* ── ALL TOPICS STATUS ── */}
				{tab === "all" && (
					<div>
						<div style={{ marginBottom: 16, color: "#94a3b8", fontSize: 13 }}>
							Lista completa de tópicos com status sugerido: usar, fundir ou
							excluir.
						</div>

						<div style={{ display: "grid", gap: 10 }}>
							{active.allTopicsStatus.map((item) => (
								<div
									key={item.id}
									style={{
										background: "#13172a",
										border: "1px solid #1e3a5f",
										borderRadius: 10,
										padding: "12px 16px",
										display: "flex",
										justifyContent: "space-between",
										alignItems: "center",
										gap: 16,
									}}
								>
									<div>
										<div
											style={{ display: "flex", alignItems: "center", gap: 8 }}
										>
											<span
												style={{
													fontSize: 13,
													fontWeight: 700,
													color: "#f8fafc",
												}}
											>
												Tópico #{item.id}
											</span>
											<span
												style={{
													fontSize: 10,
													letterSpacing: 1,
													padding: "2px 6px",
													borderRadius: 6,
													background:
														item.status === "Excluir"
															? "#ef444420"
															: item.status === "Fundir"
																? "#f59e0b20"
																: "#10b98120",
													color:
														item.status === "Excluir"
															? "#ef4444"
															: item.status === "Fundir"
																? "#f59e0b"
																: "#10b981",
													border: `1px solid ${item.status === "Excluir" ? "#ef444430" : item.status === "Fundir" ? "#f59e0b30" : "#10b98130"}`,
												}}
											>
												{item.status}
											</span>
										</div>
										<div
											style={{ fontSize: 12, color: "#7dd3fc", marginTop: 4 }}
										>
											{item.theme}
										</div>
										<div
											style={{
												display: "flex",
												flexWrap: "wrap",
												gap: 6,
												marginTop: 6,
											}}
										>
											{item.keywords.map((kw) => (
												<span
													key={kw}
													style={{
														fontSize: 10,
														background: "#0f172a",
														color: "#94a3b8",
														padding: "2px 6px",
														borderRadius: 4,
														border: "1px solid #1e3a5f",
													}}
												>
													{kw}
												</span>
											))}
										</div>
									</div>

									<div style={{ textAlign: "right", flexShrink: 0 }}>
										<div
											style={{
												fontSize: 16,
												fontWeight: 700,
												color: "#f8fafc",
											}}
										>
											{item.size} docs
										</div>
									</div>
								</div>
							))}
						</div>
					</div>
				)}
			</div>
		</div>
	);
}

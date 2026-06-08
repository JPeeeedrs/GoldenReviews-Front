import { useMemo, useState } from "react";
import groupedTopics from "../../topics_analizers/grouped_topics_llm.json";

const numberFormat = (value) =>
	new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 1 }).format(value);

const integerFormat = (value) =>
	new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 0 }).format(value);

export default function ReviewAnalysis({ data }) {
	const [topicView, setTopicView] = useState("positive");

	const getMappedTheme = (topicId) => {
		if (topicId === undefined || topicId === null) return null;

		const normalizedId = String(
			typeof topicId === "number" ? Math.trunc(topicId) : parseInt(topicId, 10),
		);

		return groupedTopics[normalizedId] || null;
	};

	const orderedTopics = useMemo(() => {
		if (!data?.topics) return [];
		const topicsArray = data.topics[topicView] || [];
		return topicsArray
			.filter((topic) => {
				const mapped = getMappedTheme(topic.topic_id);
				return (
					!mapped?.toLowerCase().includes("lixo") &&
					!mapped?.toLowerCase().includes("descart") &&
					!mapped?.toLowerCase().includes("opinião") &&
					!mapped?.toLowerCase().includes("recomendações")
				);
			})
			.slice(0, 10);
	}, [data?.topics, topicView]);

	if (!data) return null;

	const game = data.game || {};
	const summary = data.summary || {};
	const metadata = data.metadata || {};
	const meta = data.meta || {};

	const owners = game?.owners ?? game?.steamspy?.owners;
	const totalSteamReviews =
		game?.total_reviews ?? game?.steamspy?.total_reviews ?? null;
	const avgHours = summary?.avg_hours;

	const aiSummary = summary?.ai_text_summary;
	const aiSummaryText =
		typeof aiSummary === "object" ? aiSummary?.resumo : aiSummary;
	const aiNota = typeof aiSummary === "object" ? aiSummary?.nota_ia : null;

	return (
		<section className='analysis'>
			<header className='analysis-hero'>
				<div>
					<p className='eyebrow'>GOLDEN REVIEWS • JOGO EM ANÁLISE</p>
					<h2>{game?.name ?? ""}</h2>
					<div className='meta-line'>
						{(aiNota ?? summary?.overall_score) !== undefined && (
							<span>
								⭐ {numberFormat(aiNota ?? summary.overall_score)} Score Geral
								(IA)
							</span>
						)}
						{avgHours !== undefined && avgHours !== null && (
							<span>⏱️ {numberFormat(avgHours)} h médias jogadas</span>
						)}
						{game?.release_date && <span>📅 {game.release_date}</span>}
						{game?.price && <span>💰 {game.price}</span>}
					</div>
					{game?.short_description && (
						<p className='description'>{game.short_description}</p>
					)}
				</div>
				{game?.header_image && (
					<img
						src={game.header_image}
						alt={game?.name}
						className='game-cover'
					/>
				)}
			</header>

			{aiSummaryText && (
				<div className='ai-summary-box'>
					<div className='ai-summary-header'>
						<h3>✨ Opinião dos Jogadores (Resumo IA)</h3>
						{aiNota !== null && <span>⭐ {numberFormat(aiNota)} / 5.0</span>}
					</div>
					<p>{aiSummaryText}</p>
				</div>
			)}

			<div className='stat-grid'>
				<div className='stat-card'>
					<span>Reviews processadas</span>
					<strong>{integerFormat(summary?.reviews_analyzed ?? 0)}</strong>
				</div>
				<div className='stat-card good'>
					<span>Positivas</span>
					<strong>
						{integerFormat(summary?.positive_count ?? 0)} •{" "}
						{summary?.positive_percentage ?? 0}%
					</strong>
				</div>
				<div className='stat-card bad'>
					<span>Negativas</span>
					<strong>
						{integerFormat(summary?.negative_count ?? 0)} •{" "}
						{summary?.negative_percentage ?? 0}%
					</strong>
				</div>
				<div className='stat-card neutral'>
					<span>Idioma / limite</span>
					<strong>
						{meta?.language === "brazilian" ? "PT-BR" : meta?.language}
						&nbsp;•&nbsp;
						{integerFormat(meta?.maxReviewsRequested ?? 0)} máx.
					</strong>
				</div>
				{owners && (
					<div className='stat-card highlight'>
						<span>🧾 Estimativa de cópias (SteamSpy)</span>
						<strong>{owners}</strong>
					</div>
				)}
				{totalSteamReviews && (
					<div className='stat-card highlight'>
						<span>🗳️ Reviews totais na Steam</span>
						<strong>{integerFormat(totalSteamReviews)}</strong>
					</div>
				)}
				{metadata?.processing_time_seconds !== undefined && (
					<div className='stat-card neutral'>
						<span>Processamento IA</span>
						<strong>
							{metadata.processing_time_seconds}s &nbsp;•&nbsp;
							{metadata.model_version || "BERTopic"}
						</strong>
					</div>
				)}
			</div>

			<div className='topics-header'>
				<h3>Tópicos {topicView === "positive" ? "positivos" : "negativos"}</h3>
				<button
					type='button'
					className='topics-toggle'
					onClick={() =>
						setTopicView((current) =>
							current === "positive" ? "negative" : "positive",
						)
					}
				>
					{topicView === "positive" ? "Ver negativos" : "Ver positivos"}
				</button>
			</div>

			<div className='topics-grid'>
				{orderedTopics.map((topic, idx) => {
					const examples = topic?.quotes ?? [];
					const count = topic?.mentions ?? 0;
					const keywords = topic?.keywords?.slice(0, 3).join(", ");

					// Lógica de agrupamento:
					// Se o topic ID existir no JSON, usa o tema da IA. Se não, usa o original (o original é o topic.topic)
					const mappedTheme = getMappedTheme(topic.topic_id);
					console.log(
						"topic_id:",
						topic.topic_id,
						"tipo:",
						typeof topic.topic_id,
						"→ mappedTheme:",
						mappedTheme,
					);
					console.log("topic completo:", topic);
					return (
						<div className={`topic-card ${topicView}`} key={`topic-${idx}`}>
							<div className='topic-header'>
								<strong>
									{mappedTheme
										? mappedTheme.toUpperCase()
										: topic.topic?.toUpperCase()}
								</strong>
								<span>{integerFormat(count)} menções</span>
							</div>
							<div className='topic-columns'>
								<div>
									<p className='eyebrow'>
										Score semântico: {numberFormat(topic.score)} / 5.0
									</p>
									<p
										className='eyebrow'
										style={{ marginTop: "-8px", fontStyle: "italic" }}
									>
										[{keywords}]
									</p>
									{examples.length ? (
										examples.map((sentence, i) => (
											<span key={`q-${i}`}>"{sentence}"</span>
										))
									) : (
										<span className='muted'>Sem frases representativas.</span>
									)}
								</div>
							</div>
						</div>
					);
				})}
				{orderedTopics.length === 0 && (
					<p className='muted'>Nenhum tópico encontrado para este viés.</p>
				)}
			</div>
		</section>
	);
}

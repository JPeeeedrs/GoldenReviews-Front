import groupedTopics from "../../topics_analizers/grouped_topics_llm.json";
import { useState, useMemo } from "react";

import "../styles/topicsgrid.css";

const numberFormat = (value) =>
	new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 1 }).format(value);

const integerFormat = (value) =>
	new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 0 }).format(value);

const getMappedTheme = (topicId) => {
	if (topicId === undefined || topicId === null) return null;
	const normalizedId = String(
		typeof topicId === "number" ? Math.trunc(topicId) : parseInt(topicId, 10),
	);
	return groupedTopics[normalizedId] || null;
};

const FILTERED_THEMES = ["lixo", "descart", "opinião", "recomendações"];
const isFiltered = (theme) =>
	FILTERED_THEMES.some((f) => theme?.toLowerCase().includes(f));

export default function TopicsGrid({ topics }) {
	const [topicView, setTopicView] = useState("positive");

	const orderedTopics = useMemo(() => {
		if (!topics) return [];

		const grouped = {};

		(topics[topicView] || []).forEach((topic) => {
			const mappedTheme = getMappedTheme(topic.topic_id) || topic.topic;
			if (isFiltered(mappedTheme)) return;

			if (!grouped[mappedTheme]) {
				grouped[mappedTheme] = {
					...topic,
					theme: mappedTheme,
					mentions: 0,
					quotes: [],
					score: 0,
					_count: 0,
				};
			}

			grouped[mappedTheme].mentions += topic.mentions ?? 0;
			grouped[mappedTheme].quotes.push(...(topic.quotes ?? []));
			grouped[mappedTheme].score += topic.score ?? 0;
			grouped[mappedTheme]._count += 1;
		});

		return Object.values(grouped)
			.map((t) => ({
				...t,
				score: t._count > 0 ? t.score / t._count : 0,
				quotes: t.quotes.slice(0, 5),
			}))
			.sort((a, b) => b.mentions - a.mentions)
			.slice(0, 10);
	}, [topics, topicView]);

	const themeStats = useMemo(() => {
		if (!topics) return [];
		const stats = {};

		const processTopics = (topicsArray, type) => {
			topicsArray.forEach((topic) => {
				const mappedTheme = getMappedTheme(topic.topic_id) || topic.topic;
				if (isFiltered(mappedTheme)) return;

				if (!stats[mappedTheme]) {
					stats[mappedTheme] = {
						theme: mappedTheme,
						positive: 0,
						negative: 0,
						total: 0,
					};
				}
				stats[mappedTheme][type] += topic.mentions;
				stats[mappedTheme].total += topic.mentions;
			});
		};

		processTopics(topics.positive || [], "positive");
		processTopics(topics.negative || [], "negative");

		return Object.values(stats)
			.filter((s) => s.total > 0)
			.sort((a, b) => b.total - a.total);
	}, [topics]);

	return (
		<>
			<div className='topics-header'>
				<h3>Tópicos {topicView === "positive" ? "positivos" : "negativos"}</h3>
				<button
					type='button'
					className='topics-toggle'
					onClick={() =>
						setTopicView((c) => (c === "positive" ? "negative" : "positive"))
					}
				>
					{topicView === "positive" ? "Ver negativos" : "Ver positivos"}
				</button>
			</div>

			<div className='topics-grid'>
				{orderedTopics.map((topic, idx) => {
					const examples = topic?.quotes ?? [];
					const count = topic?.mentions ?? 0;
					const mappedTheme = getMappedTheme(topic.topic_id);

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

				{themeStats.length > 0 && (
					<div className='themes-overview'>
						<h3>Visão Geral por Temas</h3>
						<div className='themes-list'>
							{themeStats.map((stat, idx) => {
								const posPct =
									Math.round((stat.positive / stat.total) * 100) || 0;
								const negPct =
									Math.round((stat.negative / stat.total) * 100) || 0;

								return (
									<div className='theme-row' key={`theme-stat-${idx}`}>
										<div className='theme-info'>
											<strong>{stat.theme.toUpperCase()}</strong>
											<span className='theme-mentions'>
												{integerFormat(stat.total)} menções totais
											</span>
										</div>
										<div className='review-bar-container'>
											<div
												className='review-bar positive'
												style={{ width: `${posPct}%` }}
												title={`${posPct}% Positivas`}
											/>
											<div
												className='review-bar negative'
												style={{ width: `${negPct}%` }}
												title={`${negPct}% Negativas`}
											/>
										</div>
										<div className='review-labels'>
											<span className='label-pos'>
												{integerFormat(stat.positive)} ({posPct}%)
											</span>
											<span className='label-neg'>
												{integerFormat(stat.negative)} ({negPct}%)
											</span>
										</div>
									</div>
								);
							})}
						</div>
					</div>
				)}
			</div>
		</>
	);
}

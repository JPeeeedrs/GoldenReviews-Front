import groupedTopics from "./grouped_topics.json";
import React from "react";

export default function TopicAnalysis() {
	return (
		<div style={{ padding: "20px", color: "white" }}>
			<h1>Painel de Análise de Tópicos (De-Para)</h1>
			<p>
				Estes são os tópicos do BERTopic fundidos nos Macro-Temas pela
				Inteligência Artificial.
			</p>

			{Object.entries(groupedTopics).map(([themeName, subTopics]) => {
				if (subTopics.length === 0) return null; // Não exibe temas vazios

				return (
					<div
						key={themeName}
						style={{
							marginBottom: "20px",
							padding: "15px",
							background: "#1e1e24",
							borderRadius: "8px",
						}}
					>
						<h2 style={{ color: "#f8b10b" }}>{themeName}</h2>

						<ul style={{ listStyleType: "none", padding: 0 }}>
							{subTopics.map((sub) => (
								<li
									key={sub.topic_id}
									style={{
										marginBottom: "10px",
										padding: "10px",
										background: "#2a2a35",
										borderRadius: "5px",
									}}
								>
									<strong>ID Original: {sub.topic_id}</strong> <br />
									<span>
										Palavras-chave: <i>{sub.words.join(", ")}</i>
									</span>{" "}
									<br />
									<span style={{ fontSize: "0.85em", color: "#aaa" }}>
										Match com a regra:{" "}
										{Math.round(sub.score_similaridade * 100)}%
									</span>
								</li>
							))}
						</ul>
					</div>
				);
			})}
		</div>
	);
}

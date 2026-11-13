"""Whitelist do vulture — uso dinâmico que a análise estática não enxerga.

Três categorias:
1. Campos Pydantic: lidos por serialização (model_dump), não por atributo.
2. Métodos de Protocol: definem o contrato; implementações vêm em blocos futuros.
3. Membros de enum: referenciados por valor em dados, não sempre por atributo.

Mantida à mão; revisar ao rodar make map. Não é código executável do projeto.
"""

from research.map_relations.core import ingest_contract, models, protocols
from research.map_relations.core.states import InvalidTransition

# ── campos Pydantic (serializados via model_dump / JSON Schema) ───────────────

models.Entity.description
models.Entity.project_id
models.Entity.preferred_name
models.Alias.source
models.Alias.confidence
models.Mention.segment_id
models.Segment.source_id
models.Claim.claim_key
models.Claim.claim_class
models.Claim.confidence
models.Participation.participation_key
models.Participation.confidence
models.Evidence.evidence_key
models.Evidence.target_id
models.Evidence.source_id
models.Evidence.quote
models.TimeScope.target_id
models.Pass.level
models.ChangeLog.action
models.ChangeLog.target_id
models.ChangeLog.before
models.ChangeLog.after
models.Note.target_id
ingest_contract.Paragraph.source_id
models.Mention.surface
models.RelationType.definition
models.RelationType.version
models.Source.published_at
models.Segment.chapter
models.TimeScope.story_time
models.TimeScope.story_order
models.TimeScope.published_at
models.TimeScope.chapter
models.TimeScope.duration
models.Lens.question
models.Lens.relation_types
models.Lens.scope
models.Lens.retrieval
models.Lens.evidence_rule
models.Lens.max_calls
models.Pass.lens_id
models.Pass.target
models.Pass.calls
models.Pass.proposed
models.Pass.verified
models.Pass.stop_reason
models.Run.task
models.Run.engine
models.Run.model
models.Run.prompt_version
models.Run.input_tokens
models.Run.output_tokens
models.Run.status
models.ChangeLog.created_at
models.Note.kind
models.Note.content
models.Note.created_at
ingest_contract.QualityReport.pages

# ── atributos de exceção (lidos por quem captura) ─────────────────────────────

InvalidTransition.current
InvalidTransition.new
InvalidTransition.actor

# ── métodos de Protocol e contrato do motor (implementações em blocos futuros) ─

protocols.LlmEngine.capabilities
protocols.LlmEngine.complete
protocols.LlmRequest.messages
protocols.LlmRequest.max_output_tokens
protocols.LlmRequest.temperature
protocols.InvalidResponse
protocols.AuthError
protocols.NetworkError
protocols.Aborted
protocols.SourceConnector.list_documents
protocols.SourceConnector.fetch
protocols.DocumentParser.parse
protocols.ProjectStore.save
protocols.ProjectStore.get
protocols.ProjectStore.list
protocols.LlmCapabilities.json_schema
protocols.LlmCapabilities.max_context_tokens
protocols.LlmCapabilities.runs_locally
protocols.LlmCapabilities.data_policy_note
protocols.LlmRequest.metadata
protocols.LlmResponse.parsed_json
protocols.LlmResponse.usage
protocols.LlmResponse.finish_reason
protocols.LlmResponse.raw
protocols.RateLimited.retry_at

# ── membros de enum (valores vêm de dados) ────────────────────────────────────

models.EntityKind.pessoa
models.EntityKind.grupo
models.EntityKind.lugar
models.EntityKind.objeto
models.EntityKind.evento
models.TargetType.entity
models.ClaimClass.afirmada
models.ClaimClass.inferida
models.ClaimClass.coocorrencia
models.ClaimClass.interpretacao
models.Role.autor
models.Role.alvo
models.Role.testemunha
models.Role.beneficiario
models.Role.participante
models.Actor.auto
models.Actor.humano
models.ChangeAction.create
models.ChangeAction.update
models.ChangeAction.delete
models.RunStatus.running
models.RunStatus.done
models.RunStatus.failed
models.RunStatus.aborted
models.LensScope.document
models.LensScope.chapter
models.LensScope.segment
models.LensRetrieval.full
models.LensRetrieval.windowed
models.LensRetrieval.semantic
models.LensEvidenceRule.required
models.LensEvidenceRule.optional
models.LensEvidenceRule.forbidden
models.PassStopReason.max_calls
models.PassStopReason.no_new_claims
models.PassStopReason.error
models.PassStopReason.completed
models.NoteKind.comment
models.NoteKind.correction
models.NoteKind.question
models.NoteKind.observation
ingest_contract.RemovalReason.rodape

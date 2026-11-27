"""Lembretes do TEO: avisar na tela quando chegar a hora.

Vale ENQUANTO O TEO ESTIVER ABERTO (decisao do dono do projeto): e' um timer do
proprio processo, nao cron/systemd. Fechar o TEO apaga os lembretes pendentes -
por isso a resposta da ferramenta diz isso, e o modelo repete para a pessoa.

O aviso sai pelo canal da tela (`ctx.avisar`, ligado no ChatCore): linha na
conversa + som/notificacao do /aviso quando a tela sabe fazer isso.
"""

import threading

from bgh.i18n import t

SPEC = {
    "type": "function",
    "function": {
        "name": "lembrete",
        "description": (
            "Marca um lembrete para daqui a N minutos (ex.: 'me lembre do remedio "
            "em 20 minutos'). O aviso aparece na tela do TEO e faz som quando a "
            "hora chega. SO' funciona enquanto o TEO estiver aberto: se a pessoa "
            "fechar, o lembrete se perde - diga isso a ela."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "minutos": {"type": "number",
                            "description": "Daqui a quantos minutos (aceita 0.5, 2, 90)"},
                "texto": {"type": "string",
                          "description": "O que devo lembrar (frase curta)"},
            },
            "required": ["minutos", "texto"],
        },
    },
}

# Teto de lembretes pendentes: modelo em loop nao pode encher a memoria do processo.
MAX_PENDENTES = 20
_PENDENTES: list = []


def _quando(minutos: float) -> str:
    """'30 segundos' / '10 minutos' / '2 horas' (o numero que a pessoa le)."""
    if minutos < 1:
        return t("lembrete.segundos", s=max(1, int(round(minutos * 60))))
    if minutos < 60:
        return t("lembrete.minutos", m=f"{minutos:g}")
    return t("lembrete.horas", h=f"{minutos / 60:g}")


def run(args: dict, ctx) -> str:
    texto = str(args.get("texto") or "").strip()
    try:
        minutos = float(str(args.get("minutos", "")).replace(",", "."))
    except (TypeError, ValueError):
        return t("lembrete.bad_min")
    if not texto:
        return t("lembrete.bad_text")
    if not 0 < minutos <= 24 * 60:
        return t("lembrete.bad_range")
    avisar = getattr(ctx, "avisar", None)
    if not callable(avisar):
        # Tela sem canal de aviso (ex.: teste/chamada direta): nao promete o que
        # nao vai acontecer.
        return t("lembrete.sem_canal")
    _PENDENTES[:] = [p for p in _PENDENTES if p.is_alive()]
    if len(_PENDENTES) >= MAX_PENDENTES:
        return t("lembrete.cheio", n=MAX_PENDENTES)

    def _dispara() -> None:
        try:
            avisar(t("lembrete.agora", texto=texto))
        except Exception:  # noqa: BLE001 - aviso nunca derruba o processo
            pass

    timer = threading.Timer(minutos * 60.0, _dispara)
    timer.daemon = True   # fechar o TEO nao espera lembrete nenhum
    timer.start()
    _PENDENTES.append(timer)
    return t("lembrete.ok", quando=_quando(minutos), texto=texto)

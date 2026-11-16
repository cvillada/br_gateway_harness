/* Tela do TEO no navegador.
 * Sem framework, sem CDN, sem build: o TEO precisa abrir na maquina do cliente
 * mesmo sem internet. O servidor fala por SSE (/api/eventos) e a pagina fala
 * por POST curto. Toda frase visivel vem de /api/inicio (bgh/i18n.py).
 */
"use strict";

var strings = {};
var ocupado = false;
var passo = 0;
var perguntaAtual = null;
var canais = {};
var fluxo = null;
var encerrado = false;
var dicaTexto = "";
var relogio = null;      // contador de segundos do turno em andamento
var segundos = 0;
var ajudaCaixa = null;   // o menu fica num cartao unico (nunca tres copias)
var ajudaItens = [];     // pares [comando, explicacao] vindos de /api/inicio
var idiomaAtual = "";    // muda pelo /lingua: a tela se reescreve no sinal de vida
var ultimoSeq = 0;       // trava de replay: evento ja visto nao desenha de novo
var versaoApp = "";      // versao mostrada ao lado do modelo, na linha de cima

function $(id) { return document.getElementById(id); }
function t(chave) { return strings[chave] || chave; }

/* ---------------- inicio ---------------- */
fetch("/api/inicio", { headers: { "Accept": "application/json" } })
  .then(function (r) {
    if (!r.ok) { throw new Error("inicio " + r.status); }
    return r.json();
  })
  .then(function (dados) {
    strings = dados.strings || {};
    pintar(dados.cores || {});
    montarTextos(dados);
    ligarBotoes();
    abrirFluxo();
  })
  .catch(function () {
    document.body.insertAdjacentHTML("afterbegin",
      "<div class='faixa-rede'>" + t("app.sessao") + "</div>");
  });

/* Linha de cima (nome do modelo + versao). Fica numa funcao porque o modelo
 * muda ao vivo: /provedor e /modelo antes so apareciam depois de recarregar. */
function mostrarModelo(nome) {
  $("sub").textContent = (nome || "") + (versaoApp ? "  v" + versaoApp : "");
}

/* ---------------- textos e cores ---------------- */
function montarTextos(dados) {
  document.title = "TEO";
  versaoApp = dados.versao || "";
  mostrarModelo(dados.modelo);
  $("enviar").textContent = t("app.enviar");
  $("sair").textContent = t("app.fechar");
  $("ajuda").textContent = t("app.ajuda");
  $("terminal").textContent = t("app.terminal");
  if (dados.ajuda) { ajudaItens = dados.ajuda; }
  idiomaAtual = dados.lingua || "";
  dicaTexto = dados.dica || t("app.dica");
  $("dica").textContent = dicaTexto;
  $("texto").placeholder = t("app.placeholder");
  $("rotulo-texto").textContent = t("app.escreva_aqui");
  $("painel-titulo").textContent = t("app.ferramentas");
  $("ctx-titulo").textContent = t("app.contexto");
  $("vazio").textContent = t("app.vazio");
  if (dados.rede) {
    document.body.dataset.rede = "1";
    $("faixa-rede").textContent = t("app.modo_rede");
    $("faixa-rede").hidden = false;
  } else {
    document.body.dataset.rede = "";
  }
  ocupado = !!dados.ocupado;
  aplicarOcupado();
  ajustarAltura();
  if (dados.ctx) { contexto({ pct: dados.ctx.pct, texto: dados.ctx.texto }); }
  var lista = $("ferramentas");
  if (!lista.children.length) {
    var vazio = document.createElement("li");
    vazio.className = "ferramenta vazia";
    vazio.id = "ferramentas-vazio";
    vazio.textContent = t("app.nada_feito");
    lista.appendChild(vazio);
  }
}

function pintar(cores) {
  var raiz = document.documentElement.style;
  var temFundo = cores.bg && String(cores.bg).charAt(0) === "#";
  // "padrao" no TEO = terminal sem cor de fundo escolhida. No terminal isso
  // significa "nao pinta nada"; aqui tambem: fica a tela clara do CSS. Sem esta
  // regra o fg branco do tema padrao apagava o titulo no fundo claro.
  if (!temFundo) {
    document.body.dataset.tema = "claro";
    raiz.setProperty("--sobre-accent", "#ffffff");
    raiz.setProperty("--sobre-user", "#ffffff");
    return;
  }
  var mapa = {
    bg: "--bg", fg: "--fg", dim: "--dim", accent: "--accent",
    user: "--user", hot: "--hot", err: "--erro", footer_bg: "--rodape"
  };
  Object.keys(mapa).forEach(function (chave) {
    var valor = cores[chave];
    if (valor && String(valor).charAt(0) === "#") { raiz.setProperty(mapa[chave], valor); }
  });
  document.body.dataset.tema = luminancia(cores.bg) < 0.45 ? "escuro" : "claro";
  // Texto em cima do botao e da bolha: quem decide e o brilho da cor escolhida.
  var acento = cores.accent || "#0b5394";
  raiz.setProperty("--sobre-accent", luminancia(acento) > 0.62 ? "#11131a" : "#ffffff");
  var usuario = cores.user || "#6a1b9a";
  raiz.setProperty("--sobre-user", luminancia(usuario) > 0.62 ? "#11131a" : "#ffffff");
}

function luminancia(hex) {
  try {
    var h = String(hex).replace("#", "");
    if (h.length === 3) { h = h[0] + h[0] + h[1] + h[1] + h[2] + h[2]; }
    var r = parseInt(h.slice(0, 2), 16) / 255;
    var g = parseInt(h.slice(2, 4), 16) / 255;
    var b = parseInt(h.slice(4, 6), 16) / 255;
    return 0.2126 * r + 0.7152 * g + 0.0722 * b;
  } catch (e) { return 0; }
}

/* ---------------- fluxo de eventos ---------------- */
function abrirFluxo(desde) {
  if (fluxo) { fluxo.close(); }
  var inicio = (typeof desde === "number") ? desde : 0;
  fluxo = new EventSource("/api/eventos?desde=" + inicio);
  fluxo.onopen = function () {
    faixa("");
    // Replay do buffer (aba recarregada no meio de um turno) chega logo depois:
    // a varredura cobre a resposta que ja estava na tela.
    setTimeout(function () { ligarCaminhos(); }, 800);
  };
  fluxo.onerror = function () {
    if (encerrado) { return; }
    faixa(t("app.caiu"));
    // Reconecta pedindo SO o que falta (ultimoSeq). Sem isso, uma queda de
    // conexao podia reenviar o buffer inteiro e ressuscitar o menu de ajuda
    // no meio de uma resposta qualquer.
    fluxo.close();
    setTimeout(function () { if (!encerrado) { abrirFluxo(ultimoSeq); } }, 1500);
  };
  fluxo.onmessage = function (ev) {
    var dados;
    try { dados = JSON.parse(ev.data); } catch (e) { return; }
    if (typeof dados.seq === "number") {
      if (dados.seq <= ultimoSeq) { return; }   // ja desenhado: nao repete
      ultimoSeq = dados.seq;
    }
    tratar(dados);
  };
}

function faixa(texto) {
  var el = $("faixa-rede");
  if (texto) {
    el.textContent = texto;
    el.hidden = false;
  } else if (document.body.dataset.rede === "1") {
    el.textContent = t("app.modo_rede");
    el.hidden = false;
  } else {
    el.hidden = true;
  }
}

function tratar(e) {
  switch (e.tipo) {
    case "linha": linha(e.texto, e.estilo); break;
    case "partes": partes(e.partes); break;
    case "sep": break;                       // o cartao do canal ja separa
    case "borda": break;                     // no app os cartoes ja separam
    case "delta": delta(e.canal, e.texto); break;
    case "ferramenta": ferramenta(e); break;
    case "ctx": contexto(e); break;
    case "estado": ocupado = !!e.ocupado; aplicarOcupado(); break;
    case "modelo": mostrarModelo(e.modelo); break;
    case "rodada": passo += 1; mostrarPasso(); break;
    case "pergunta": pergunta(e); break;
    case "pergunta_fechada": fecharPergunta(e.id); break;
    case "preencher": $("texto").value = e.texto || ""; ajustarAltura(); $("texto").focus(); break;
    case "tema": pintar(e.cores || {}); break;
    case "bip": bip(); break;
    case "fim_turno": fimTurno(); break;
    case "encerrando": encerrar(e.motivo || ""); break;
    default: break;
  }
}

/* ---------------- desenho do historico ---------------- */
function conversa() { return $("conversa"); }

function pertoDoFim() {
  var c = conversa();
  return (c.scrollTop + c.clientHeight) >= (c.scrollHeight - 140);
}

function rolar(antes) {
  if (antes) {
    var c = conversa();
    // Salto instantaneo, e nao a rolagem suave do CSS: a animacao era cortada
    // pelo reflow seguinte (a faixa de "TEO trabalhando" entra, a caixa de
    // digitar cresce) e a ultima linha da mensagem ficava cortada no meio pela
    // borda de baixo da conversa.
    c.style.scrollBehavior = "auto";
    c.scrollTop = c.scrollHeight;
    c.style.scrollBehavior = "";
  }
}

function limparVazio() {
  var v = $("vazio");
  if (v && v.parentNode) { v.parentNode.removeChild(v); }
}

function acrescentar(el) {
  var estava = pertoDoFim();
  limparVazio();
  conversa().appendChild(el);
  rolar(estava);
}

function linha(texto, estilo) {
  if (texto === undefined || texto === null) { return; }
  var el = document.createElement("div");
  el.className = "linha" + (estilo ? " " + String(estilo).replace("class:", "") : "");
  el.textContent = String(texto);
  acrescentar(el);
}

function linhaDePartes(lista) {
  var el = document.createElement("div");
  el.className = "partes";
  (lista || []).forEach(function (par) {
    var span = document.createElement("span");
    // O core alinha com espacos a direita (f"{comando:<{width}}"); na coluna do
    // flex esses espacos so deixariam o comando "solto" - tiro do fim.
    span.textContent = String(par[0]).replace(/\s+$/, "");
    var estilo = par[1] || "";
    if (estilo === "bold") { span.style.fontWeight = "700"; }
    else if (estilo === "dim") { span.style.color = "var(--dim)"; }
    else if (estilo === "cyan") { span.style.color = "var(--accent)"; }
    else if (String(estilo).charAt(0) === "#") { span.style.color = estilo; }
    el.appendChild(span);
  });
  return el;
}

function partes(lista) {
  // Linhas montadas em pedacos (ex.: /lingua). No app a ajuda NAO passa por aqui:
  // ela e propria da tela e vem pronta no /api/inicio.
  acrescentar(linhaDePartes(lista));
}

function cartaoAjuda() {
  // Um unico cartao de ajuda por vez: pedir /ajuda tres vezes nao pode deixar
  // tres manuais empilhados na conversa (aconteceu no teste do dono do projeto).
  var antigos = document.querySelectorAll(".cartao.ajuda");
  for (var i = 0; i < antigos.length; i++) {
    if (antigos[i].parentNode) { antigos[i].parentNode.removeChild(antigos[i]); }
  }
  var el = document.createElement("div");
  el.className = "cartao ajuda";
  var topo = document.createElement("div");
  topo.className = "cartao-topo";
  var ponto = document.createElement("span");
  ponto.className = "ponto";
  var rotulo = document.createElement("span");
  rotulo.textContent = t("app.opcoes");
  var fechar = document.createElement("button");
  fechar.type = "button";
  fechar.className = "ver-rascunho";
  fechar.textContent = t("app.fechar_menu") || "x";
  fechar.addEventListener("click", function () {
    if (el.parentNode) { el.parentNode.removeChild(el); }
    ajudaCaixa = null;
  });
  topo.appendChild(ponto);
  topo.appendChild(rotulo);
  topo.appendChild(fechar);
  var corpo = document.createElement("div");
  corpo.className = "ajuda-lista";
  el.appendChild(topo);
  el.appendChild(corpo);
  return { raiz: el, corpo: corpo };
}

function bolha(texto, recado) {
  var el = document.createElement("div");
  el.className = "bolha" + (recado ? " recado" : "");
  el.textContent = texto;
  acrescentar(el);
}

function cartao(canal) {
  var el = document.createElement("div");
  el.className = "cartao " + (canal === "pensamento" ? "rascunho fechado" : "resposta");
  var topo = document.createElement("div");
  topo.className = "cartao-topo";
  var ponto = document.createElement("span");
  ponto.className = "ponto";
  topo.appendChild(ponto);
  var rotulo = document.createElement("span");
  rotulo.textContent = canal === "pensamento" ? t("app.pensamento") : "TEO";
  topo.appendChild(rotulo);
  var corpo = document.createElement("div");
  corpo.className = "rascunho-corpo";
  if (canal === "pensamento") {
    el.classList.add("pensando");
    var ver = document.createElement("button");
    ver.type = "button";
    ver.className = "ver-rascunho";
    ver.textContent = t("app.ver_rascunho");
    ver.addEventListener("click", function () {
      var fechado = el.classList.toggle("fechado");
      ver.textContent = fechado ? t("app.ver_rascunho") : t("app.esconder");
    });
    topo.appendChild(ver);
  }
  el.appendChild(topo);
  el.appendChild(corpo);
  return { raiz: el, corpo: corpo };
}

function delta(canal, texto) {
  if (!texto) { return; }
  var caixa = canais[canal];
  if (!caixa) {
    caixa = cartao(canal);
    canais[canal] = caixa;
    acrescentar(caixa.raiz);
  }
  var estava = pertoDoFim();
  caixa.corpo.appendChild(document.createTextNode(String(texto)));
  var c = conversa();
  if (estava) { c.scrollTop = c.scrollHeight; }
}

/* ---------------- documento citado: caminho vira link -------------------- */
/* A resposta do TEO cita o caminho do arquivo que ele acabou de criar. Antes era
 * so texto: a pessoa tinha que copiar e procurar na mao. Agora o caminho de
 * documento vira link e abre em OUTRA janela (a conversa fica onde esta).
 * Lista fechada de tipos, igual a do servidor: so o que ele serve.
 */
var DOC_EXTS = ["pdf", "txt", "log", "md", "csv", "tsv", "json", "png", "jpg",
                "jpeg", "gif", "webp", "bmp", "docx", "doc", "xlsx", "xls",
                "pptx", "ppt", "odt", "ods", "odp", "rtf", "epub", "zip"];
/* Caminho pode ter ESPACO no nome ("/home/ana/Meus Documentos/Contas.pdf"):
 * o candidato vai ate a extensao de documento e quem decide se existe e o
 * servidor (checar=1). Assim nao aparece link morto na tela de uma crianca ou
 * de um idoso, e caminho com espaco funciona igual ao sem espaco.
 * A lista de extensoes aqui tem que ser a MESMA de DOC_EXTS (a suite confere).
 */
var DOC_RE = /(^|[\s("'`<\[])((?:~?\/)[^"'\n<>|]*?\.(?:pdf|txt|log|md|csv|tsv|json|png|jpg|jpeg|gif|webp|bmp|docx|doc|xlsx|xls|pptx|ppt|odt|ods|odp|rtf|epub|zip))(?![A-Za-z0-9])/gi;

function candidatosDeDocumento(texto) {
  var achados = [];
  var m;
  DOC_RE.lastIndex = 0;
  while ((m = DOC_RE.exec(texto)) !== null) {
    var inicio = m.index + m[1].length;
    var bruto = m[2].replace(/[.,;:!?]+$/, "");
    if (bruto.length > 2) { achados.push({ inicio: inicio, texto: bruto }); }
    if (DOC_RE.lastIndex <= m.index) { DOC_RE.lastIndex = m.index + 1; }
  }
  return achados;
}

function conferirDocumento(caminho) {
  // O servidor responde 204 se o arquivo existe e pode ser aberto.
  return fetch("/api/arquivo?checar=1&c=" + encodeURIComponent(caminho))
    .then(function (r) { return r.ok; })
    .catch(function () { return false; });
}

/* Um trecho pode juntar dois caminhos ("veja /home/a e depois /home/b.pdf").
 * Se o caminho inteiro nao existe, tenta os pedacos que comecam num "/" mais a
 * frente - o mais longo primeiro, que e o caso normal e gasta uma pergunta so.
 */
function conferirCandidato(cand) {
  var opcoes = [cand.texto];
  for (var i = 1; i < cand.texto.length; i++) {
    if (cand.texto.charAt(i) === "/") { opcoes.push(cand.texto.slice(i)); }
  }
  var cadeia = Promise.resolve(null);
  opcoes.forEach(function (opcao) {
    cadeia = cadeia.then(function (achado) {
      if (achado) { return achado; }
      return conferirDocumento(opcao).then(function (ok) {
        if (!ok) { return null; }
        return { inicio: cand.inicio + (cand.texto.length - opcao.length),
                 texto: opcao };
      });
    });
  });
  return cadeia;
}

function montarComLinks(el, achados) {
  var texto = el.textContent || "";
  var frag = document.createDocumentFragment();
  var pos = 0;
  achados.forEach(function (achado) {
    if (achado.inicio < pos) { return; }
    if (achado.inicio > pos) {
      frag.appendChild(document.createTextNode(texto.slice(pos, achado.inicio)));
    }
    var a = document.createElement("a");
    a.className = "arquivo";
    a.href = "/api/arquivo?c=" + encodeURIComponent(achado.texto);
    a.target = "_blank";                    // nova janela/aba: a conversa nao sai
    a.rel = "noopener noreferrer";
    a.textContent = achado.texto;
    a.title = t("app.abrir_arquivo");
    frag.appendChild(a);
    pos = achado.inicio + achado.texto.length;
  });
  if (pos < texto.length) {
    frag.appendChild(document.createTextNode(texto.slice(pos)));
  }
  el.textContent = "";
  el.appendChild(frag);
}

function ligarCaminhos(raiz) {
  var alvos = (raiz || document).querySelectorAll(
    ".cartao.resposta .rascunho-corpo, .linha");
  for (var i = 0; i < alvos.length; i++) {
    (function (el) {
      if (el.dataset.ligado === "1" || el.dataset.ligando === "1") { return; }
      var texto = el.textContent || "";
      if (texto.indexOf("/") < 0) { el.dataset.ligado = "1"; return; }
      var cands = candidatosDeDocumento(texto);
      if (!cands.length) { el.dataset.ligado = "1"; return; }
      el.dataset.ligando = "1";
      Promise.all(cands.map(conferirCandidato))
        .then(function (achados) {
          var bons = achados.filter(function (a) { return a; })
                             .sort(function (a, b) { return a.inicio - b.inicio; });
          if (bons.length) { montarComLinks(el, bons); }
        })
        .catch(function () { /* sem rede: fica texto, como antes */ })
        .then(function () {
          delete el.dataset.ligando;
          el.dataset.ligado = "1";
        });
    })(alvos[i]);
  }
}

function ferramenta(e) {
  var lista = $("ferramentas");
  var vazio = $("ferramentas-vazio");
  if (vazio && vazio.parentNode) { vazio.parentNode.removeChild(vazio); }
  var item = document.createElement("li");
  item.className = "ferramenta";
  var nome = document.createElement("b");
  nome.textContent = e.nome || "?";
  var det = document.createElement("code");
  det.textContent = e.preview || "";
  item.appendChild(nome);
  item.appendChild(det);
  lista.insertBefore(item, lista.firstChild);
  while (lista.children.length > 12) { lista.removeChild(lista.lastChild); }
}

function contexto(e) {
  var pct = (typeof e.pct === "number") ? e.pct : 0;
  var barra = $("ctx-barra");
  barra.style.width = Math.max(0, Math.min(pct, 100)) + "%";
  barra.classList.toggle("alto", pct >= 85);
  $("ctx-pct").textContent = pct + "%";
  $("ctx-texto").textContent = e.texto || "";
  var pai = barra.parentNode;
  pai.setAttribute("aria-valuenow", String(pct));
  pai.setAttribute("aria-valuetext", pct + "%");
}

function mostrarPasso() {
  var el = $("passo");
  if (passo > 1) {
    el.textContent = t("app.passo").replace("{n}", String(passo));
    el.hidden = false;
  }
}

function fimTurno() {
  Object.keys(canais).forEach(function (canal) {
    var caixa = canais[canal];
    caixa.raiz.classList.remove("pensando");
    if (canal === "pensamento" && !caixa.corpo.textContent.trim()) {
      if (caixa.raiz.parentNode) { caixa.raiz.parentNode.removeChild(caixa.raiz); }
    }
  });
  canais = {};
  ocupado = false;
  aplicarOcupado();
  // Fim do turno = resposta completa: agora o caminho de documento pode virar
  // link (durante o streaming o texto ainda esta pela metade).
  ligarCaminhos();
}

/* ---------------- caixa de digitar ---------------- */
function ligarBotoes() {
  $("enviar").addEventListener("click", function () {
    if (ocupado) { parar(); } else { enviar(); }
  });
  $("sair").addEventListener("click", sair);
  $("ajuda").addEventListener("click", ajuda);
  $("terminal").addEventListener("click", irParaTerminal);
  var caixa = $("texto");
  caixa.addEventListener("input", ajustarAltura);
  caixa.addEventListener("keydown", function (ev) {
    if (ev.key === "Enter" && !ev.shiftKey) {
      ev.preventDefault();
      enviar();
    }
  });
  document.addEventListener("keydown", function (ev) {
    if (ev.key === "Escape" && perguntaAtual) {
      ev.preventDefault();
      responder(perguntaAtual.padrao);
    }
  });
  ajustarAltura();
}

function ajustarAltura() {
  var caixa = $("texto");
  if (!caixa) { return; }
  // A caixa crescendo tambem come altura da conversa: quem esta no fim nao pode
  // ficar com a ultima linha cortada.
  var estavaNoFim = pertoDoFim();
  caixa.style.height = "auto";
  caixa.style.height = Math.min(caixa.scrollHeight + 4, 180) + "px";
  rolar(estavaNoFim);
}

function enviar(silencioso) {
  var caixa = $("texto");
  var texto = caixa.value.trim();
  if (!texto) { return; }
  // Barra sozinha abre a lista de opcoes do TEO (no terminal o "/" abre a pasta;
  // aqui nao existe pasta, entao abre a lista de comandos da tela).
  if (texto === "/") {
    caixa.value = "";
    ajustarAltura();
    if (!ocupado) { ajuda(); }
    return;
  }
  // /ajuda digitado a mao abre a MESMA ajuda da tela (nao o manual do terminal).
  if (/^\/(ajuda|help|ayuda)\b/i.test(texto)) {
    caixa.value = "";
    ajustarAltura();
    ajuda();
    return;
  }
  // /terminal ou /tui digitado: faz o mesmo do botao Terminal.
  if (/^\/(terminal|tui)\b/i.test(texto)) {
    caixa.value = "";
    ajustarAltura();
    irParaTerminal();
    return;
  }
  if (!silencioso) { bolha(texto, ocupado); }
  caixa.value = "";
  ajustarAltura();
  fetch("/api/turno", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ texto: texto })
  }).catch(function () { linha(t("app.caiu"), "red"); });
}

function parar() {
  fetch("/api/parar", { method: "POST" }).catch(function () {});
}

function ajuda() {
  // Ajuda da PROPRIA tela: curta, so o que existe no navegador. Vem pronta do
  // /api/inicio (bloco app.cmd.* / app.help.* do i18n) - nao passa pelo core.
  var botao = $("ajuda");
  if (ocupado || botao.disabled) { return; }
  var jaTem = document.querySelector(".cartao.ajuda");
  if (jaTem) {
    jaTem.scrollIntoView({ block: "nearest", behavior: "smooth" });
    return;
  }
  var caixa = cartaoAjuda();
  (ajudaItens || []).forEach(function (par) {
    // Os pedacos de uma linha sao [texto, estilo]. Item = comando + explicacao;
    // secao vem sem explicacao e o CSS desenha como cabecalho.
    if (par[1]) {
      caixa.corpo.appendChild(linhaDePartes([[par[0], ""], [par[1], ""]]));
    } else {
      caixa.corpo.appendChild(linhaDePartes([[par[0], ""]]));
    }
  });
  acrescentar(caixa.raiz);
  caixa.raiz.scrollIntoView({ block: "nearest", behavior: "smooth" });
  ajudaCaixa = caixa;
}

function sair() {
  // Pergunta SEMPRE, nao so durante o turno: o botao fica no alto e um clique
  // sem querer fechava o TEO inteiro (aconteceu no teste do dono do projeto).
  var aviso = ocupado ? t("app.sair_confirmar") : t("app.sair_ok");
  if (!window.confirm(aviso)) { return; }
  fetch("/api/sair", { method: "POST" }).catch(function () {});
}

function irParaTerminal() {
  // Fecha a tela e o processo do TEO continua no terminal de onde ele foi aberto.
  if (ocupado) { return; }
  if (!window.confirm(t("app.terminal.aviso"))) { return; }
  fetch("/api/terminal", { method: "POST" }).catch(function () {});
}

function aplicarOcupado() {
  // A faixa muda a ALTURA do rodape: a conversa encolhe alguns pixels e, sem
  // devolver a rolagem, a ultima linha da mensagem da pessoa ficava cortada no
  // meio pela borda. Mede o "estava no fim" ANTES de mexer no layout.
  var estavaNoFim = pertoDoFim();
  var botao = $("enviar");
  botao.textContent = ocupado ? t("app.parar") : t("app.enviar");
  botao.classList.toggle("parar", ocupado);
  // Ajuda manda comando: durante o turno o core nao aceita comando, entao o
  // botao fica desligado em vez de virar um recado estranho no meio da resposta.
  $("ajuda").disabled = ocupado;
  $("terminal").disabled = ocupado;
  $("dica").textContent = ocupado ? t("app.trabalhando") : dicaTexto;
  // Marca no corpo da pagina: o CSS pinta o campo e a dica durante o turno.
  document.body.classList.toggle("ocupado", ocupado);
  // Faixa visivel acima da linha de digitar: rodinha girando, texto e a barra
  // correndo dizem "esta vivo e ocupado" sem precisar ler a frase pequena.
  var faixa = $("trabalhando");
  if (faixa) {
    faixa.hidden = !ocupado;
    var rotulo = $("trabalhando-texto");
    if (rotulo) { rotulo.textContent = ocupado ? t("app.trabalhando_curto") : ""; }
  }
  if (ocupado) { comecarRelogio(); } else { pararRelogio(); }
  // Devolve a leitura no fim da conversa depois da mudanca de altura.
  rolar(estavaNoFim);
}

/* Contador do turno: "7 s", "1:12". E o sinal mais honesto de que o TEO nao
 * travou - o numero sobe enquanto ele trabalha. */
function comecarRelogio() {
  if (relogio) { return; }
  segundos = 0;
  mostrarTempo();
  relogio = setInterval(function () {
    segundos += 1;
    mostrarTempo();
  }, 1000);
}

function pararRelogio() {
  if (relogio) { clearInterval(relogio); relogio = null; }
  segundos = 0;
  mostrarTempo();
}

function mostrarTempo() {
  var el = $("trabalhando-tempo");
  if (!el) { return; }
  if (segundos <= 0) { el.textContent = ""; return; }
  var minutos = Math.floor(segundos / 60);
  var resto = segundos % 60;
  el.textContent = minutos
    ? minutos + ":" + (resto < 10 ? "0" : "") + resto
    : segundos + " s";
}

/* ---------------- sinal de vida ---------------- */
/* A cada 12s a pagina avisa que esta aberta. E isso que separa "a pessoa esta
 * na frente da tela" de "a aba foi fechada" (queda de TCP nao e confiavel).
 * A resposta traz o idioma: se mudou pelo /lingua, a tela se reescreve. */
setInterval(function () {
  if (encerrado) { return; }
  fetch("/api/vivo", { method: "POST" })
    .then(function (r) { return r.ok ? r.json() : null; })
    .then(function (d) {
      if (d && d.lingua && idiomaAtual && d.lingua !== idiomaAtual) {
        idiomaAtual = d.lingua;
        recarregarTextos();
      }
    })
    .catch(function () {});
}, 12000);

function recarregarTextos() {
  fetch("/api/inicio", { headers: { "Accept": "application/json" } })
    .then(function (r) { return r.ok ? r.json() : null; })
    .then(function (d) {
      if (!d) { return; }
      strings = d.strings || strings;
      if (d.ajuda) { ajudaItens = d.ajuda; }
      pintar(d.cores || {});
      montarTextos(d);
      // A ajuda aberta era do idioma antigo: fecha e deixa pedir de novo.
      var velho = document.querySelector(".cartao.ajuda");
      if (velho && velho.parentNode) {
        velho.parentNode.removeChild(velho);
        ajudaCaixa = null;
      }
    })
    .catch(function () {});
}

/* ---------------- licenca / perguntas ---------------- */
function pergunta(e) {
  perguntaAtual = { id: e.id, padrao: "" };
  $("m-titulo").textContent = e.titulo || t("app.licenca_titulo");
  $("m-dica").textContent = (e.modo === "opcoes") ? t("app.licenca_dica") : "";
  $("m-label").textContent = e.label || "";
  $("m-detalhe").textContent = e.detalhe || "";
  var opcoes = $("m-opcoes");
  var campo = $("m-campo");
  opcoes.textContent = "";
  $("m-texto").hidden = true;
  $("m-ok").hidden = true;
  campo.hidden = true;

  if (e.modo === "texto") {
    campo.hidden = false;
    $("m-texto").hidden = false;
    $("m-ok").hidden = false;
    $("m-texto").type = e.secret ? "password" : "text";
    $("m-texto").value = "";
    $("m-texto").placeholder = "";
    $("m-ok").textContent = t("app.enviar");
    $("m-ok").onclick = function () { responder($("m-texto").value); };
    $("m-texto").onkeydown = function (ev) {
      if (ev.key === "Enter") { ev.preventDefault(); responder($("m-texto").value); }
    };
    perguntaAtual.padrao = e.valor || "";
  } else {
    perguntaAtual.padrao = "";
    (e.opcoes || []).forEach(function (op) {
      var b = document.createElement("button");
      b.type = "button";
      b.className = "opcao" + (op.tom ? " " + op.tom : "");
      var marca = document.createElement("span");
      marca.className = "marca-opcao";
      marca.textContent = op.tom === "nao" ? "\u00d7" : (op.tom === "bom" ? "\u2713" : "");
      var rotulo = document.createElement("span");
      rotulo.textContent = op.texto;
      b.appendChild(marca);
      b.appendChild(rotulo);
      b.addEventListener("click", function () { responder(op.codigo); });
      opcoes.appendChild(b);
      perguntaAtual.padrao = op.codigo;      // o ULTIMO e o "nao": ESC nega
    });
  }

  $("veu").hidden = false;
  setTimeout(function () {
    var alvo = (e.modo === "texto") ? $("m-texto")
      : opcoes.querySelector(".opcao:last-child");
    if (alvo) { alvo.focus(); }
  }, 30);
}

function responder(valor) {
  if (!perguntaAtual) { return; }
  var id = perguntaAtual.id;
  perguntaAtual = null;
  $("veu").hidden = true;
  fetch("/api/responder", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ id: id, valor: String(valor) })
  }).catch(function () {});
  $("texto").focus();
}

function fecharPergunta(id) {
  if (perguntaAtual && perguntaAtual.id === id) {
    perguntaAtual = null;
    $("veu").hidden = true;
  }
}

/* ---------------- fim ---------------- */
function encerrar(motivo) {
  encerrado = true;
  if (fluxo) { fluxo.close(); }
  ocupado = false;
  pararRelogio();          // cala o contador do turno
  var faixaTrabalho = $("trabalhando");
  if (faixaTrabalho) { faixaTrabalho.hidden = true; }
  document.body.classList.remove("ocupado");
  $("veu").hidden = true;
  $("fim-titulo").textContent = (motivo === "terminal")
    ? t("app.abrindo_terminal") : t("app.encerrando");
  $("fim-texto").textContent = "";
  $("veu-fim").hidden = false;
  $("texto").disabled = true;
  $("enviar").disabled = true;
}

function bip() {
  try {
    var Ctx = window.AudioContext || window.webkitAudioContext;
    if (!Ctx) { return; }
    var ctx = new Ctx();
    var osc = ctx.createOscillator();
    var ganho = ctx.createGain();
    osc.type = "sine";
    osc.frequency.value = 880;
    ganho.gain.value = 0.06;
    osc.connect(ganho);
    ganho.connect(ctx.destination);
    osc.start();
    setTimeout(function () {
      osc.stop();
      if (ctx.close) { ctx.close(); }
    }, 140);
  } catch (e) { /* som e enfeite: nunca quebra a tela */ }
}

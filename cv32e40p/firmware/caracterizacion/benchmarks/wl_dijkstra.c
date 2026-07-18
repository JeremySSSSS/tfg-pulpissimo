/* Dijkstra real: caminos minimos desde cada nodo de un grafo de 32 nodos
 * (matriz de adyacencia generada deterministicamente). Codigo C normal:
 * busqueda del minimo, relajacion de aristas, memoria y control. */
#ifndef REPS
#define REPS 6000
#endif

#define V 32
#define INF 0x3fffffff

static unsigned g[V][V];
static unsigned dist[V];
static unsigned char vis[V];

static void build_graph(void) {
  unsigned s = 0x1234567u;
  for (int i = 0; i < V; i++)
    for (int j = 0; j < V; j++) {
      s = s * 1103515245u + 12345u;             /* LCG clasico */
      unsigned w = (s >> 16) & 255u;
      g[i][j] = (i == j) ? 0 : (w < 64 ? INF : w);   /* ~25% sin arista */
    }
}

static unsigned dijkstra(int src) {
  for (int i = 0; i < V; i++) { dist[i] = INF; vis[i] = 0; }
  dist[src] = 0;
  for (int it = 0; it < V; it++) {
    int u = -1; unsigned best = INF;
    for (int i = 0; i < V; i++)
      if (!vis[i] && dist[i] < best) { best = dist[i]; u = i; }
    if (u < 0) break;
    vis[u] = 1;
    for (int w = 0; w < V; w++)
      if (g[u][w] != INF && dist[u] + g[u][w] < dist[w])
        dist[w] = dist[u] + g[u][w];
  }
  unsigned acc = 0;
  for (int i = 0; i < V; i++) acc += dist[i];
  return acc;
}

void run_workload(void) {
  volatile unsigned sink = 0;
  build_graph();
  for (int r = 0; r < REPS; r++)
    sink += dijkstra(r & (V - 1));
}

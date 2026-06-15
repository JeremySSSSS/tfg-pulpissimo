/* Dijkstra: camino mas corto de fuente unica en grafo denso (algoritmo real,
 * grafos). Matriz de adyacencia NxN, O(N^2). Mezcla natural: ALU (sumas,
 * comparaciones), MEM (matriz/vectores), CTRL (busqueda del minimo y relajacion
 * data-dependent, ramas que dependen de los datos -> irregular como gcd/sort),
 * MUL (indexado 2D adj[u][v] = u*N+v). Entero, sin libc. */
#ifndef REPS
#define REPS 4000
#endif
#define N 80
#define INF 0x3fffffff

static int adj[N][N];
static int dist[N];
static unsigned char done[N];

void run_workload(void){
  /* grafo determinista con pesos pseudo-aleatorios (xorshift, sin libc) */
  unsigned s=2463534242u;
  for(int i=0;i<N;i++)
    for(int j=0;j<N;j++){
      s^=s<<13; s^=s>>17; s^=s<<5;
      adj[i][j] = (i==j) ? 0 : (int)(1 + (s % 20));
    }

  volatile int sink=0;
  for(int rep=0; rep<REPS; rep++){
    int src = rep % N;
    for(int i=0;i<N;i++){ dist[i]=INF; done[i]=0; }
    dist[src]=0;
    for(int it=0; it<N; it++){
      int u=-1, best=INF;
      for(int i=0;i<N;i++)                 /* extrae el minimo no visitado */
        if(!done[i] && dist[i]<best){ best=dist[i]; u=i; }
      if(u<0) break;
      done[u]=1;
      for(int v=0;v<N;v++){                /* relaja vecinos */
        int w=adj[u][v];
        if(w && !done[v] && dist[u]+w < dist[v])
          dist[v]=dist[u]+w;
      }
    }
    sink += dist[(src + N/2) % N];
  }
  (void)sink;
}

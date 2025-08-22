
from connection.Red import Red

class SolveDjstra():
  def __init__(self, miRed: Red):
      self.red = miRed

  def minDistance(self, dist, sptSet):
        min = 1e7
        min_index = 0
        for v in range(self.red.V):
            if dist[v] < min and sptSet[v] == False:
                min = dist[v]
                min_index = v

        return min_index
  def printSolution(self, dist):
    print("Vertex \t Distance from Source")
    for node in range(self.red.V):
       print(node, "\t\t", dist[node])

  def dijkstra(self, src):
    dist = [1e7] * self.red.V
    dist[src] = 0
    sptSet = [False] * self.red.V
    for cout in range(self.red.V):
      u = self.minDistance(dist, sptSet)
      sptSet[u] = True
      for v in range(self.V):
          if (self.red.graph[u][v] > 0 and 
              sptSet[v] == False and 
              dist[v] > dist[u] + self.red.graph[u][v]):
              dist[v] = dist[u] + self.red.graph[u][v]

    self.printSolution(dist)

    return dist
  
  
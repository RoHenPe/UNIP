using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;
using UnityEngine.SceneManagement;

public class Spawner : MonoBehaviour
{
    [SerializeField] GameObject barrilprefab;
    [SerializeField] float time = 2f;
    [SerializeField] float minY = -2f, maxY = 2f;

    private bool isPaused = false; // Variável para controlar o estado do Spawner
    private List<Move00> barrils = new List<Move00>(); // Lista para armazenar todos os Barrils criados

    // Start is called before the first frame update
    void Start()
    {
        InvokeRepeating(nameof(Spawn), time, time); 
    }

    void Spawn()
    {
        // Verifica se o Spawner está pausado antes de gerar um novo Barril
        if (!isPaused)
        {
            GameObject newBarril = Instantiate(barrilprefab, transform.position, Quaternion.identity);
            Move00 move00 = newBarril.AddComponent<Move00>();
            newBarril.transform.position += new Vector3(0, Random.Range(minY, maxY));
            barrils.Add(move00); // Adiciona o novo Barril à lista
        }
    }

    // Método para pausar o Spawner e todos os Barrils criados
    public void Pause()
    {
        isPaused = true;
        foreach (Move00 barril in barrils)
        {
            barril.Pause();
        }
    }

    // Método para retomar o Spawner e todos os Barrils criados
    public void Resume()
    {
        isPaused = false;
        foreach (Move00 barril in barrils)
        {
            barril.Resume();
        }
    }
}

using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;
using UnityEngine.SceneManagement;

public class GameManager : MonoBehaviour
{
    [Header("Componentes de UI")]
    [SerializeField] private Text scoreText;
    [SerializeField] private GameObject GameOverObj;
    [SerializeField] private Button bossButton; 
    [SerializeField] private GameObject startImage; // <-- IMAGEM DE INÍCIO

    [Header("Controle do Jogo")]
    [SerializeField] private Spawner spawner;
    private int score;
    private bool gamePaused = false;

    [Header("Lógica do Boss")]
    private int bossClickCount = 0;
    private bool isBossActive = false;
    private int scoreAtBossAppearance;

    void Start()
    {
        Time.timeScale = 1;
        GameOverObj.SetActive(false);
        bossButton.gameObject.SetActive(false);

        // Inicia a rotina para mostrar a imagem inicial
        StartCoroutine(ShowStartImageRoutine());
    }

    // Corrotina para controlar a imagem de início
    private IEnumerator ShowStartImageRoutine()
    {
        // 1. Mostra a imagem
        startImage.SetActive(true);

        // 2. Espera por 3 segundos (você pode mudar este valor)
        yield return new WaitForSeconds(3f);

        // 3. Esconde a imagem
        startImage.SetActive(false);
    }

    void Update()
    {
        if (isBossActive && score >= scoreAtBossAppearance + 5)
        {
            Debug.Log("O jogador não derrotou o boss a tempo! Fim de jogo.");
            GameOver();
        }
    }

    public void Scoring()
    {
        if (gamePaused) return; 

        score++;
        scoreText.text = score.ToString();

        if (score % 10 == 0 && !isBossActive)
        {
            ActivateBossSequence();
        }
    }

    private void ActivateBossSequence()
    {
        Debug.Log("O BOSS APARECEU!");
        isBossActive = true;
        bossClickCount = 0;
        scoreAtBossAppearance = score;
        bossButton.gameObject.SetActive(true);
    }

    public void OnBossButtonClicked()
    {
        if (!isBossActive) return;

        bossClickCount++;
        Debug.Log("Botão do Boss clicado! Contagem: " + bossClickCount);

        if (bossClickCount >= 2)
        {
            Debug.Log("Boss derrotado!");
            isBossActive = false;
            bossButton.gameObject.SetActive(false); 
        }
    }

    public void GameOver()
    {
        if (GameOverObj != null)
        {
            GameOverObj.SetActive(true);
        }
        Time.timeScale = 0; 
        gamePaused = true;
        if (spawner != null)
        {
            spawner.Pause();
        }
    }

    public void RestartButton()
    {
        SceneManager.LoadScene(SceneManager.GetActiveScene().buildIndex);
    }

    public bool IsGameOver()
    {
        return gamePaused;
    }
}
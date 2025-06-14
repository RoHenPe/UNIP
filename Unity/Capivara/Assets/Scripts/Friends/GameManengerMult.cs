// GameManagerMult.cs
using UnityEngine;
using UnityEngine.UI;
using UnityEngine.SceneManagement;
using Firebase.Database;

public class GameManagerMult : MonoBehaviour
{
    [Header("UI References")]
    [SerializeField] private Text scoreText1;
    [SerializeField] private Text scoreText2;
    [SerializeField] private GameObject GameOverObj;

    [Header("Game Objects")]
    [SerializeField] private GameObject player1Obj;
    [SerializeField] private GameObject player2Obj;
    [SerializeField] private SpawnerMulti barrelSpawner;

    private int score1;
    private int score2;
    private bool player1Paused = false;
    private bool player2Paused = false;

    // --- NOVAS VARIÁVEIS DE REDE ---
    private DatabaseReference opponentRef;
    private GameObject localPlayerObj;
    private GameObject opponentPlayerObj;
    private Text localScoreText;
    private Text opponentScoreText;
    private Vector3 opponentTargetPosition;
    private bool opponentIsAlive = true;

    void Start()
    {
        Time.timeScale = 1;
        GameOverObj.SetActive(false);
        if (barrelSpawner != null) barrelSpawner.Resume();
        
        SetupPlayers();
        SetupFirebaseListeners();
    }
    
    void SetupPlayers()
    {
        // Define quem é o jogador local e quem é o oponente
        if (GameSession.PlayerNumber == 1)
        {
            localPlayerObj = player1Obj;
            opponentPlayerObj = player2Obj;
            localScoreText = scoreText1;
            opponentScoreText = scoreText2;
            opponentRef = FirebaseDatabase.DefaultInstance.RootReference.Child("game_rooms").Child(GameSession.RoomId).Child("player2_data");
        }
        else if (GameSession.PlayerNumber == 2)
        {
            localPlayerObj = player2Obj;
            opponentPlayerObj = player1Obj;
            localScoreText = scoreText2;
            opponentScoreText = scoreText1;
            opponentRef = FirebaseDatabase.DefaultInstance.RootReference.Child("game_rooms").Child(GameSession.RoomId).Child("player1_data");
        }
        else
        {
            Debug.LogWarning("Modo de teste local. A sincronização não funcionará.");
            localPlayerObj = player1Obj;
            opponentPlayerObj = player2Obj;
            localScoreText = scoreText1;
            opponentScoreText = scoreText2;
            // Desativa os controles para evitar erros.
            player1Obj.GetComponent<Player1>().enabled = false;
            player2Obj.GetComponent<Player2>().enabled = false;
            return;
        }

        // Ativa o controle do jogador local e desativa o do oponente
        localPlayerObj.GetComponent<MonoBehaviour>().enabled = true;
        opponentPlayerObj.GetComponent<MonoBehaviour>().enabled = false;

        // Inicia a posição do oponente na posição atual dele para evitar saltos
        opponentTargetPosition = opponentPlayerObj.transform.position;
    }

    void SetupFirebaseListeners()
    {
        if(opponentRef == null) return; // Não cria listeners em modo de teste

        // Listener para a posição do oponente
        opponentRef.Child("posY").ValueChanged += (sender, args) =>
        {
            if (args.Snapshot.Exists)
            {
                float opponentY = float.Parse(args.Snapshot.Value.ToString());
                opponentTargetPosition.y = opponentY;
            }
        };

        // Listener para a pontuação do oponente
        opponentRef.Child("score").ValueChanged += (sender, args) =>
        {
            if (args.Snapshot.Exists)
            {
                opponentScoreText.text = args.Snapshot.Value.ToString();
            }
        };

        // Listener para o estado (vivo/morto) do oponente
        opponentRef.Child("isAlive").ValueChanged += (sender, args) =>
        {
            if (args.Snapshot.Exists)
            {
                opponentIsAlive = (bool)args.Snapshot.Value;
                if (!opponentIsAlive)
                {
                    opponentPlayerObj.SetActive(false);
                    CheckForGameOver();
                }
            }
        };
    }

    void Update()
    {
        // Interpola suavemente a posição do oponente para evitar movimentos bruscos
        if (opponentPlayerObj.activeSelf)
        {
            opponentPlayerObj.transform.position = Vector3.Lerp(opponentPlayerObj.transform.position, opponentTargetPosition, Time.deltaTime * 10);
        }
    }

    private void CheckForGameOver()
    {
        bool localPlayerIsAlive = (GameSession.PlayerNumber == 1 && !player1Paused) || (GameSession.PlayerNumber == 2 && !player2Paused);
        if (!localPlayerIsAlive && !opponentIsAlive)
        {
            GameOver();
        }
    }

    public void GameOver()
    {
        GameOverObj.SetActive(true);
        if (barrelSpawner != null) barrelSpawner.Pause();
    }
    
    // --- MÉTODOS DE JOGO ATUALIZADOS ---
    public void PausePlayer1()
    {
        player1Paused = true;
        player1Obj.SetActive(false);
        if(GameSession.PlayerNumber == 1) FirebaseManager.Instance.UpdatePlayerStatus(false);
        CheckForGameOver();
    }

    public void PausePlayer2()
    {
        player2Paused = true;
        player2Obj.SetActive(false);
        if(GameSession.PlayerNumber == 2) FirebaseManager.Instance.UpdatePlayerStatus(false);
        CheckForGameOver();
    }

    public void ScoringPlayer1()
    {
        score1++;
        scoreText1.text = score1.ToString();
        if(GameSession.PlayerNumber == 1) FirebaseManager.Instance.UpdatePlayerScore(score1);
    }

    public void ScoringPlayer2()
    {
        score2++;
        scoreText2.text = score2.ToString();
        if(GameSession.PlayerNumber == 2) FirebaseManager.Instance.UpdatePlayerScore(score2);
    }

    // --- FUNÇÕES QUE NÃO MUDAM ---
    public void RestartButton()
    {
        SceneManager.LoadScene(SceneManager.GetActiveScene().buildIndex);
    }

    public bool IsGameOver()
    {
        return player1Paused && player2Paused;
    }
}
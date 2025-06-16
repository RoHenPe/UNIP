using UnityEngine;
using UnityEngine.SceneManagement;

public class MudoSom : MonoBehaviour
{
    [SerializeField] AudioSource Mudo;

    void Awake()
    {
        // Define a tag deste objeto como "MusicaMenu" para que ele possa ser encontrado depois.
        gameObject.tag = "MusicaMenu";

        // Procura por QUALQUER outro objeto que também tenha a tag "MusicaMenu".
        GameObject[] outrasMusicas = GameObject.FindGameObjectsWithTag("MusicaMenu");

        // Para cada música antiga encontrada...
        foreach (GameObject musica in outrasMusicas)
        {
            // ...se não for este mesmo objeto, significa que é a música da vez passada.
            if (musica != this.gameObject)
            {
                // Destrói a música antiga.
                Destroy(musica);
            }
        }

        // Marca este objeto para não ser destruído ao mudar de cena.
        // Assim, quando o menu recarregar, este script poderá encontrá-lo e "matá-lo".
        DontDestroyOnLoad(this.gameObject);
        
        // Toca a música, caso ela não esteja tocando.
        if (!Mudo.isPlaying)
        {
            Mudo.Play();
        }
    }
    
    public void LigarDesligarSom()
    {
        bool EstadoSom = !Mudo.isPlaying;
        Mudo.enabled = EstadoSom;

        PlayerPrefs.SetInt("EstadoSom", EstadoSom ? 1 : 0);

        if (EstadoSom)
        {
            Mudo.Play();
        }
        else
        {
            Mudo.Stop();
        }
    }
}
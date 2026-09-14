package br.preparatorio.player;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

@RestController
public class PlayerController {

    @GetMapping("/api/player/profile")
    public Map<String, Object> profile(
            @RequestParam(defaultValue = "demo") String id
    ) {
        return Map.of(
                "id", id,
                "name", "Jogador PREPARATÓRIO",
                "level", 1,
                "xp", 0,
                "profession", "Técnico de Enfermagem",
                "cameraDefault", "third-person",
                "cameraAlternative", "first-person"
        );
    }
}

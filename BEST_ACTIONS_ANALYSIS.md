# Analiza Najlepszych Akcji Ruchu (Vis-Sol SWARM AI)

Na podstawie analizy rzeczywistych logów z symulacji (`train_sim_20260127_064742.csv`), wybrano trzy kluczowe scenariusze, które najlepiej demonstrują inteligencję i skuteczność systemu nawigacji SWARM AI.

## 1. Szybkie Unikanie Przeszkody (Rapid Obstacle Avoidance)
*   **Zakres:** Cykle 220 - 252 (Czas trwania: ~1.6s)
*   **Kontekst:** Robot napotyka nagłą przeszkodę bezpośrednio przed sobą podczas szybkiego ruchu.
*   **Działanie AI:** System wykrywa spadek odczytu sensora przedniego poniżej progu bezpieczeństwa (200mm). W ciągu milisekund podejmowana jest decyzja o manewrze wymijającym.
*   **Rezultat:** Robot skutecznie omija przeszkodę minimalną korektą kursu, utrzymując płynność ruchu bez zatrzymania.
*   **Wizualizacje:**
    *   Ścieżka ruchu: `scenario_0_Avoidance.png`
    *   Odczyty sensorów: `scenario_0_Avoidance_sensors.png`
    *   **Animacja przebiegu:** `scenario_0_Avoidance.gif`

## 2. Stabilna Nawigacja w Wąskim Korytarzu (Narrow Passage)
*   **Zakres:** Cykle 6924 - 7471 (Czas trwania: ~27s)
*   **Kontekst:** Przejazd przez długi, wąski korytarz, gdzie oba sensory boczne wskazują bliskość ścian (<150mm).
*   **Działanie AI:** System utrzymuje kierunek `FORWARD` z mikrokorektami, skutecznie tłumiąc tendencję do oscylacji (efekt "ping-pong") dzięki algorytmom stabilizacji.
*   **Rezultat:** Płynny przejazd przez trudny odcinek bez kolizji.
*   **Wizualizacje:**
    *   Ścieżka ruchu: `scenario_2_Narrow_Passage.png`
    *   Odczyty sensorów: `scenario_2_Narrow_Passage_sensors.png`
    *   **Animacja przebiegu:** `scenario_2_Narrow_Passage.gif`

## 3. Złożone Manewry Omijania (Extended Avoidance)
*   **Zakres:** Cykle 3910 - 4103 (Czas trwania: ~9.5s)
*   **Kontekst:** Sytuacja wymagająca dłuższego, wieloetapowego manewru omijania większej przeszkody.
*   **Działanie AI:** Robot wykonuje serię skoordynowanych skrętów, stale monitorując odległość od przeszkody, aż do znalezienia wolnej przestrzeni.
*   **Rezultat:** Skuteczne wyjście z trudnej sytuacji nawigacyjnej.
*   **Wizualizacje:**
    *   Ścieżka ruchu: `scenario_1_Avoidance.png`
    *   Odczyty sensorów: `scenario_1_Avoidance_sensors.png`
    *   **Animacja przebiegu:** `scenario_1_Avoidance.gif`

---
*Wizualizacje i animacje wygenerowane na podstawie danych: train_sim_20260127_064742.csv*

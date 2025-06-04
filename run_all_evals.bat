@echo off
echo Running all evaluation configurations...

echo.
echo ===== Running minigames_test =====
python evals\run_eval.py minigames_test --output all_evals_minigames_test

echo.
echo ===== Running minigames_comparison =====
python evals\run_eval.py minigames_comparison --output all_evals_minigames_comparison

echo.
echo ===== All evaluations complete! =====
echo Check evals\reports\ for results.
pause 
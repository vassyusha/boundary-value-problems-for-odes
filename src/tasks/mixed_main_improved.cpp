#include "tasks/mixed_main_improved.hpp"

#include "solver.hpp"
#include "task_utils.hpp"

#include <algorithm>
#include <cmath>
#include <iomanip>
#include <sstream>
#include <stdexcept>
#include <utility>
#include <vector>

namespace {

struct GridSolution {
    int n = 0;
    std::vector<double> values;
};

struct AccuracyCheck {
    double epsilon = 0.0;
    double x = 0.0;
    int index = 0;
};

constexpr double kPi = 3.141592653589793238462643383279502884;

double integralExpMinusSquare(double left, double right) {
    return 0.5 * std::sqrt(kPi) * (std::erf(right) - std::erf(left));
}

double integrateInvK(double left, double right, double xi) {
    if (right <= left) {
        return 0.0;
    }
    if (right <= xi) {
        return right - left;
    }
    if (left >= xi) {
        return integralExpMinusSquare(left, right);
    }
    return (xi - left) + integralExpMinusSquare(xi, right);
}

double integrateQ(double left, double right, double xi) {
    const auto qLeftPrimitive = [](double x) {
        return x * x * x / 3.0;
    };
    const auto qRightPrimitive = [](double x) {
        return x + x * x * x * x * x / 5.0;
    };

    if (right <= left) {
        return 0.0;
    }
    if (right <= xi) {
        return qLeftPrimitive(right) - qLeftPrimitive(left);
    }
    if (left >= xi) {
        return qRightPrimitive(right) - qRightPrimitive(left);
    }
    return qLeftPrimitive(xi) - qLeftPrimitive(left) + qRightPrimitive(right) - qRightPrimitive(xi);
}

double integrateF(double left, double right, double xi) {
    const auto fLeftPrimitive = [](double x) {
        return x * x * x / 3.0 - x;
    };
    const auto fRightPrimitive = [](double x) {
        return x;
    };

    if (right <= left) {
        return 0.0;
    }
    if (right <= xi) {
        return fLeftPrimitive(right) - fLeftPrimitive(left);
    }
    if (left >= xi) {
        return fRightPrimitive(right) - fRightPrimitive(left);
    }
    return fLeftPrimitive(xi) - fLeftPrimitive(left) + fRightPrimitive(right) - fRightPrimitive(xi);
}

double coefficientA(int i, double h, double xi) {
    const double left = static_cast<double>(i - 1) * h;
    const double right = static_cast<double>(i) * h;
    const double integral = integrateInvK(left, right, xi);
    if (integral <= 0.0) {
        throw std::runtime_error("Invalid integral for coefficient a_i");
    }
    return h / integral;
}

double coefficientD(int i, int n, double h, double xi) {
    const double x = static_cast<double>(i) * h;
    const double left = std::max(0.0, x - 0.5 * h);
    const double right = std::min(1.0, x + 0.5 * h);
    const double width = right - left;
    return integrateQ(left, right, xi) / width;
}

double coefficientPhi(int i, int n, double h, double xi) {
    const double x = static_cast<double>(i) * h;
    const double left = std::max(0.0, x - 0.5 * h);
    const double right = std::min(1.0, x + 0.5 * h);
    const double width = right - left;
    return integrateF(left, right, xi) / width;
}

GridSolution solveForN(int n, const VariantData& variant) {
    if (n < 1) {
        throw std::runtime_error("n must be positive");
    }

    const int size = n + 1;
    const double h = 1.0 / static_cast<double>(n);
    const double h2 = h * h;
    const double xi = variant.xi;

    std::vector<double> lower(static_cast<size_t>(size - 1), 0.0);
    std::vector<double> diagonal(static_cast<size_t>(size), 0.0);
    std::vector<double> upper(static_cast<size_t>(size - 1), 0.0);
    std::vector<double> rhs(static_cast<size_t>(size), 0.0);

    diagonal[0] = 1.0;
    rhs[0] = variant.mu1;

    for (int i = 1; i <= n - 1; ++i) {
        const double aLeft = coefficientA(i, h, xi);
        const double aRight = coefficientA(i + 1, h, xi);
        const double d = coefficientD(i, n, h, xi);
        const double phi = coefficientPhi(i, n, h, xi);

        lower[static_cast<size_t>(i - 1)] = -aLeft / h2;
        diagonal[static_cast<size_t>(i)] = (aLeft + aRight) / h2 + d;
        upper[static_cast<size_t>(i)] = -aRight / h2;
        rhs[static_cast<size_t>(i)] = phi;
    }

    const double aRightBoundary = coefficientA(n, h, xi);
    const double dRightBoundary = coefficientD(n, n, h, xi);
    const double phiRightBoundary = coefficientPhi(n, n, h, xi);

    // Balance on [x_{n-1/2}, x_n] with w(1)=mu2, so k(1)u'(1)=-mu2.
    lower[static_cast<size_t>(n - 1)] = -aRightBoundary / h;
    diagonal[static_cast<size_t>(n)] = aRightBoundary / h + 0.5 * h * dRightBoundary;
    rhs[static_cast<size_t>(n)] = 0.5 * h * phiRightBoundary - variant.mu2;

    return GridSolution{n, solveTridiagonal(lower, diagonal, upper, rhs)};
}

AccuracyCheck compareOnCommonNodes(const GridSolution& coarse, const GridSolution& fine) {
    if (fine.n != 2 * coarse.n) {
        throw std::runtime_error("Fine grid must have twice as many segments as coarse grid");
    }

    AccuracyCheck check;
    for (int i = 0; i <= coarse.n; ++i) {
        const double difference = coarse.values[static_cast<size_t>(i)] - fine.values[static_cast<size_t>(2 * i)];
        const double absDifference = std::abs(difference);
        if (absDifference > check.epsilon) {
            check.epsilon = absDifference;
            check.index = i;
            check.x = static_cast<double>(i) / static_cast<double>(coarse.n);
        }
    }
    return check;
}

struct RefinedSolution {
    GridSolution coarse;
    GridSolution fine;
    AccuracyCheck check;
    bool meetsTolerance = false;
};

RefinedSolution solveWithRefinement(const InputData& input, const VariantData& variant) {
    int n = std::max(1, input.segments);
    const int maxN = std::max(n, input.maxSegments);
    const int multiplier = std::max(2, input.refinementMultiplier);

    while (true) {
        GridSolution coarse = solveForN(n, variant);
        GridSolution fine = solveForN(2 * n, variant);
        AccuracyCheck check = compareOnCommonNodes(coarse, fine);
        const bool meetsTolerance = check.epsilon <= input.tolerance;

        if (meetsTolerance || n >= maxN || n > maxN / multiplier) {
            return RefinedSolution{std::move(coarse), std::move(fine), check, meetsTolerance};
        }

        n *= multiplier;
    }
}

std::string formatScientific(double value) {
    std::ostringstream out;
    out << std::scientific << std::setprecision(6) << value;
    return out.str();
}

void fillRows(TaskResult& task, const RefinedSolution& solution, int tableStride) {
    const int stride = std::max(1, tableStride);
    const int n = solution.coarse.n;

    for (int i = 0; i <= n; i += stride) {
        const double v = solution.coarse.values[static_cast<size_t>(i)];
        const double v2 = solution.fine.values[static_cast<size_t>(2 * i)];
        task.rows.push_back(TableRow{
            i,
            static_cast<double>(i) / static_cast<double>(n),
            0.0,
            v,
            v2,
            v - v2
        });
    }

    if (task.rows.empty() || task.rows.back().index != n) {
        const double v = solution.coarse.values[static_cast<size_t>(n)];
        const double v2 = solution.fine.values[static_cast<size_t>(2 * n)];
        task.rows.push_back(TableRow{n, 1.0, 0.0, v, v2, v - v2});
    }
}

}  // namespace

TaskResult runMixedMainImprovedTask(const InputData& input, const VariantData& variant) {
    TaskResult task = makeTaskStub(
        "mixed-main-improved",
        "Смешанная краевая основная задача, улучшенная аппроксимация ГУ",
        "4. Смешанная основная, улучш. ГУ",
        "u(0)=mu1, w(1)=mu2",
        "Метод баланса на правой половинной ячейке",
        "Смешанная краевая основная задача, улучш. аппрокс. ГУ",
        makeMainTaskColumns());

    const RefinedSolution solution = solveWithRefinement(input, variant);
    fillRows(task, solution, input.tableStride);

    std::ostringstream note;
    note << "Для основной смешанной задачи использована равномерная сетка с n = "
         << solution.coarse.n << ".\n"
         << "Правое граничное условие задано как w(1)=mu2, что эквивалентно k(1)u'(1)=-mu2.\n"
         << "Улучшенная аппроксимация ГУ получена методом баланса на отрезке [x_{n-1/2}, x_n].\n"
         << "Заданная точность epsilon = " << formatScientific(input.tolerance) << ".\n"
         << "Достигнутая точность epsilon_2 = max|v(x_i)-v2(x_{2i})| = "
         << formatScientific(solution.check.epsilon) << ".\n"
         << "Максимальная разность наблюдается в узле i = " << solution.check.index
         << ", x = " << std::setprecision(10) << solution.check.x << ".\n"
         << "Статус точности: " << (solution.meetsTolerance ? "достигнута" : "не достигнута в пределах maxSegments") << ".";

    task.status = solution.meetsTolerance ? "done" : "done_tolerance_not_reached";
    task.note = note.str();
    return task;
}

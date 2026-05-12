#include "tasks/mixed_test_classic.hpp"

#include "solver.hpp"
#include "task_utils.hpp"

#include <algorithm>
#include <cmath>
#include <iomanip>
#include <sstream>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace {
    
    double u(double x, VariantData data){
    double C1 = 0.0, C2 = 0.0;
    double lymbda = 0.0;
    double partial = 0.0;
    if(x < 0 || x > 1) throw "x out of range";
    if(x < data.xi){
        C1 = 0.587133640028619;
        C2 = 3.412866359971381;
        lymbda = 1/sqrt(3); 
        partial = -2.0; 
    }
    if(x >= data.xi){
        C1 = -0.116209345000844;
        C2 =  0.936306880621530;
        lymbda = sqrt(10.0/(9.0 * exp(1.0/3.0)));
        partial = 0.9;
    }
    return C1 * exp(lymbda * x) + C2 * exp(-lymbda * x) + partial;
}

struct GridSolution {
    int n = 0;
    std::vector<double> values;
};

GridSolution solveAnalytic(int n, VariantData variant){
    std::vector<double> res(n+1);
    const double h = 1.0 / static_cast<double>(n);

    for(int i = 0; i <= n; i++){
        res[i] = u(i*h, variant);
    }
    return GridSolution{n, res};
}

struct AccuracyCheck {
    double epsilon = 0.0;
    double x = 0.0;
    int index = 0;
};

double integrateK(double left, double right, double xi) {

    const double k1_star = 1.0;
    const double k2_star = std::exp(1.0 / 3.0);
    const double inv_k1 = 1.0 / k1_star;  // = 1
    const double inv_k2 = 1.0 / k2_star;  // = e^{-1/3}
    
    if (right <= left) return 0.0;
    if (right <= xi) return inv_k1 * (right - left);
    if (left >= xi) return inv_k2 * (right - left);
    return inv_k1 * (xi - left) + inv_k2 * (right - xi);
}

double integrateQ(double left, double right, double xi) {
    const double q1 = 1.0 / 3.0;
    const double q2 = 10.0 / 9.0;
    
    if (right <= left) return 0.0;
    if (right <= xi) return q1 * (right - left);
    if (left >= xi) return q2 * (right - left);
    return q1 * (xi - left) + q2 * (right - xi);
}

double integrateF(double left, double right, double xi) {
    const double f1 = -2.0 / 3.0;
    const double f2 = 1.0;
    
    if (right <= left) return 0.0;
    if (right <= xi) return f1 * (right - left);
    if (left >= xi) return f2 * (right - left);
    return f1 * (xi - left) + f2 * (right - xi);
}

double coefficientA(int i, double h, double xi) {
    const double left = static_cast<double>(i - 1) * h;
    const double right = static_cast<double>(i) * h;
    const double integral = integrateK(left, right, xi);
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
    lower[static_cast<size_t>(n - 1)] = -aRightBoundary / h;
    diagonal[static_cast<size_t>(n)] = aRightBoundary / h;
    rhs[static_cast<size_t>(n)] = variant.mu2;

    return GridSolution{n, solveTridiagonal(lower, diagonal, upper, rhs)};
}

AccuracyCheck compareOnCommonNodes(const GridSolution& comp, const GridSolution& ana) {
    if (comp.n != ana.n) {
        throw std::runtime_error("analytic grid must have as many segments as computed grid");
    }

    AccuracyCheck check;
    for (int i = 0; i <= comp.n; ++i) {
        const double difference = comp.values[static_cast<size_t>(i)] - ana.values[static_cast<size_t>(i)];
        const double absDifference = std::abs(difference);
        if (absDifference > check.epsilon) {
            check.epsilon = absDifference;
            check.index = i;
            check.x = static_cast<double>(i) / static_cast<double>(comp.n);
        }
    }
    return check;
}

struct RefinedSolution {
    GridSolution computed;
    GridSolution analytic;
    AccuracyCheck check;
    bool meetsTolerance = false;
};

RefinedSolution solveWithRefinement(const InputData& input, const VariantData& variant) {
    int n = std::max(1, input.segments);
    const int maxN = std::max(n, input.maxSegments);
    const int multiplier = std::max(2, input.refinementMultiplier);

    while (true) {
        GridSolution comp = solveForN(n, variant);
        GridSolution ana = solveAnalytic(n, variant);
        AccuracyCheck check = compareOnCommonNodes(comp, ana);
        const bool meetsTolerance = check.epsilon <= input.tolerance;

        if (meetsTolerance || n >= maxN || n > maxN / multiplier) {
            return RefinedSolution{std::move(comp), std::move(ana), check, meetsTolerance};
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
    const int n = solution.computed.n;

    for (int i = 0; i <= n; i += stride) {
        const double v = solution.computed.values[static_cast<size_t>(i)];
        const double u = solution.analytic.values[static_cast<size_t>(i)];
        task.rows.push_back(TableRow{
            i,
            static_cast<double>(i) / static_cast<double>(n),
            u,
            v,
            0.0,
            u - v
        });
    }

    if (task.rows.empty() || task.rows.back().index != n) {
        const double v = solution.computed.values[static_cast<size_t>(n)];
        const double u = solution.analytic.values[static_cast<size_t>(n)];
        task.rows.push_back(TableRow{n, 1.0, u, v, 0.0, u - v});
    }
}

} //namespace

TaskResult runMixedTestClassicTask(const InputData& input, const VariantData& variant) {
    TaskResult result = makeTaskStub(
        "mixed-test-classic",
        "Смешанная краевая тестовая задача, классическая аппроксимация ГУ",
        "3. Смешанная тест.",
        "Смешанные граничные условия",
        "Классическая аппроксимация граничных условий",
        "Исполнитель 3",
        makeTestTaskColumns());

    const RefinedSolution solution = solveWithRefinement(input, variant);
    fillRows(result, solution, input.tableStride);

    std::ostringstream note;
    note << "Для тестовой смешанной задачи использована равномерная сетка с n = "
         << solution.computed.n << ".\n"
         << "Правое граничное условие: k(1)u'(1)=mu2. Классическая аппроксимация: "
         << "k(1)(v_n-v_{n-1})/h = mu2.\n"
         << "Коэффициенты тестовой задачи k*, q*, f* заданы как предел соответствующей функции при x -> xi слева или справа и равны:\n"
         << "k1* = 1; k2* = exp(1/3);\n"
         << "q1* = 1/3; q2* = 10/9;\n"
         << "f1* = -2/3; f2* = 1.\n"
         << "Заданная точность epsilon = " << formatScientific(input.tolerance) << ".\n"
         << "Достигнутая точность epsilon_1 = max|u(x_i)-v(x_i)| = "
         << formatScientific(solution.check.epsilon) << ".\n"
         << "Максимальная разность наблюдается в узле i = " << solution.check.index
         << ", x = " << std::setprecision(10) << solution.check.x << ".\n"
         << "Статус точности: "
         << (solution.meetsTolerance ? "достигнута" : "не достигнута в пределах maxSegments") << ".";

    result.status = solution.meetsTolerance ? "done" : "done_tolerance_not_reached";
    result.note = note.str();
    return result;
}

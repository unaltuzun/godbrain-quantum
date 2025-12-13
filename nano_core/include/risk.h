#ifndef GODBRAIN_RISK_H
#define GODBRAIN_RISK_H

#include <stdint.h>

typedef struct {
    double entry_price;
    double quantity;
    double stop_loss;
    double take_profit;
} Position;

typedef enum {
    RISK_NONE = 0,
    RISK_TP   = 1,
    RISK_SL   = 2,
    RISK_BOTH = 3
} risk_level_t;

// Branchless-ish risk kontrolü (0/1 mask)
static inline risk_level_t check_risk(const Position* pos, double last_price) {
    double pnl = (last_price - pos->entry_price) * pos->quantity;

    uint64_t is_stop_loss   = (pnl <= -pos->stop_loss) ? 1ULL : 0ULL;
    uint64_t is_take_profit = (pnl >=  pos->take_profit) ? 1ULL : 0ULL;

    return (risk_level_t)((is_stop_loss << 1) | is_take_profit);
}

#endif // GODBRAIN_RISK_H

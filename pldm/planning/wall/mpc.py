import torch
import time

from pldm_envs.utils.normalizer import Normalizer
from pldm_envs.wall.data.wall import WallDatasetConfig
from pldm_envs.wall.evaluation.create_envs import construct_eval_envs

from pldm.utils import format_seconds
from .utils import *
from pldm.models.jepa import JEPA
from pldm.planning.plotting import log_planning_plots, log_l1_planning_loss
from pldm.planning.mpc import MPCEvaluator
from pldm.planning.enums import PooledMPCResult
from pldm.planning.wall.enums import WallMPCConfig, MPCReport


class WallMPCEvaluator(MPCEvaluator):
    def __init__(
        self,
        config: WallMPCConfig,
        jepa: JEPA,
        prober: torch.nn.Module,
        normalizer: Normalizer,
        wall_config: WallDatasetConfig,
        cross_wall: bool = True,
        quick_debug: bool = False,
        prefix: str = "",
    ):
        super().__init__(
            config=config,
            model=jepa,
            prober=prober,
            normalizer=normalizer,
            quick_debug=quick_debug,
            prefix=prefix,
        )

        self.wall_config = wall_config
        self.cross_wall = cross_wall

        self.envs = construct_eval_envs(
            seed=config.seed,
            wall_config=self.wall_config,
            n_envs=config.n_envs,
            level=config.level,
            cross_wall=self.cross_wall,
            normalizer=self.normalizer,
        )

        self.wall_locs = torch.stack([e.wall_x for e in self.envs]).cpu()

    def evaluate(self):
        start_time = time.time()

        mpc_data = self._perform_mpc_in_chunks()

        elapsed_time = int(time.time() - start_time)
        print(f"mpc planning took {format_seconds(elapsed_time)}")

        report = self._construct_report(mpc_data, elapsed_time=elapsed_time)

        log_l1_planning_loss(result=mpc_data, prefix=self.prefix)

        if self.config.visualize_planning:
            log_planning_plots(
                result=mpc_data,
                report=report,
                idxs=(
                    list(range(report.errors.shape[0]))
                    if not self.quick_debug
                    else [0, 1]
                ),
                prefix=self.prefix,
                n_steps=self.config.n_steps,
                xy_action=self.wall_config.action_param_xy,
            )

        return mpc_data, report

    def _construct_report(self, data: PooledMPCResult, elapsed_time: float = 0):
        """
        Run various analytics on mpc result
        """
        config = self.config
        locations = data.locations
        targets = data.targets
        wall_locs = self.wall_locs

        terminations = determine_terminations(
            locations, targets, config.error_threshold
        )

        final_errors = torch.stack(
            [
                (
                    locations[min(terminations[i], len(locations) - 1)][i].cpu()
                    - target.cpu()
                )
                .pow(2)
                .mean()
                for i, target in enumerate(targets)
            ]
        )

        # percentage of trials where agent gets to the other side of the wall, given it started from a different side of the target
        starts, ends = locations[0], locations[-1]

        cross_wall_rate = calculate_cross_wall_rate(
            starts=starts,
            ends=ends,
            targets=targets,
            wall_locs=wall_locs,
            wall_config=self.wall_config,
        )

        # percentage of trials where agent's initial plan reaches other sideof the wall, given it started from different side of the target
        init_plan_last_loc = data.pred_locations[0][-1]
        init_plan_cross_wall_rate = calculate_cross_wall_rate(
            starts=starts,
            ends=init_plan_last_loc,
            targets=targets,
            wall_locs=wall_locs,
            wall_config=self.wall_config,
        )

        report = MPCReport(
            error_mean=final_errors.mean(),
            errors=final_errors,
            terminations=terminations,
            planning_time=elapsed_time,
            cross_wall_rate=cross_wall_rate,
            init_plan_cross_wall_rate=init_plan_cross_wall_rate,
        )

        return report

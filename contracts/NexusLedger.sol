// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract NexusLedger {
    event InsightRecorded(
        string targetTx,
        string aiAssessment,
        uint256 timestamp
    );

    function recordInsight(
        string memory _targetTx,
        string memory _aiAssessment
    ) external {
        emit InsightRecorded(_targetTx, _aiAssessment, block.timestamp);
    }
}
